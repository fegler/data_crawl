import os 
import subprocess 
from glob import glob 
import shutil 
from tqdm import tqdm
import cv2
from pathlib import Path
import numpy as np 

from scenedetect import SceneManager, open_video
from scenedetect.detectors import ContentDetector
from scenedetect.video_splitter import split_video_ffmpeg
from ultralytics import YOLO

####################
#  segment & clip  #
####################

def split_video_to_segment(video_path, output_dir, seg_duration=2) -> str:
    os.makedirs(output_dir, exist_ok=True)
    output_template = os.path.join(output_dir, "%03d.mp4")

    command = [
        "ffmpeg",
        "-i", video_path,
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-force_key_frames", f"expr:gte(t,n_forced*{seg_duration})",
        "-segment_time", str(seg_duration),
        "-f", "segment",
        "-reset_timestamps", "1",
        output_template
    ]
    subprocess.run(command, check=True)

def split_raw_to_segments_folder(segment_dir, data_dir, seg_duration=2) -> str:
    video_name = segment_dir.split('/')[-1]
    output_dir = os.path.join(data_dir, 'segments', video_name)
    os.makedirs(output_dir, exist_ok=True)
    segment_paths = glob(os.path.join(segment_dir, '*.mp4'))
    for s_path in segment_paths:
        split_video_to_segment(s_path, output_dir, seg_duration)
    return output_dir

def split_raw_to_segments_single(video_path, data_dir, seg_duration=2) -> str:
    filename = os.path.splitext(os.path.basename(video_path))[0]
    output_dir = os.path.join(data_dir, 'segments', filename)
    split_video_to_segment(video_path, output_dir, seg_duration)
    return output_dir

def save_clip_with_sampling(segment_dir, data_dir, sample_rate=5) -> str:
    video_name = segment_dir.split('/')[-1]
    output_dir = os.path.join(data_dir, 'clips', video_name)
    os.makedirs(output_dir, exist_ok=True)
    segment_paths = glob(os.path.join(segment_dir, '*.mp4'))

    for s_path in segment_paths:
        filename = os.path.splitext(os.path.basename(s_path))[0]
        output_template = os.path.join(output_dir, f"{filename}_%03d.mp4")

        command = [
            "ffmpeg",
            "-i", s_path,
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-vf", f"select='not(mod(n,{sample_rate}))',setpts=N/FRAME_RATE/TB",
            "-reset_timestamps", "1",
            "-f", "segment",
            output_template
        ]

        subprocess.run(command, check=True)

######################
##  Person Clip
######################
def extract_person_clip_folder(
    segment_dir, 
    data_dir, 
    model_ckpt="yolov8n.pt",
    offset_ratio=0.2
):
    video_name = segment_dir.split('/')[-1]
    output_dir = os.path.join(data_dir, 'person_clip', video_name)
    os.makedirs(output_dir, exist_ok=True)
    segment_paths = glob(os.path.join(segment_dir, '*.mp4'))

    model = YOLO(model_ckpt)

    for s_path in segment_paths:
        extract_person_clip(
            s_path, output_dir,
            model, offset_ratio
        )

def extract_person_clip(
    video_path,
    output_dir,
    model,
    offset_ratio=0.2
):
    cap = cv2.VideoCapture(video_path)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    center_idx = total_frames // 2 

    cap.set(cv2.CAP_PROP_POS_FRAMES, center_idx)
    
    ret, center_frame = cap.read()
    if not ret:
        print("[ERROR] Could not read center frame")
        return

    # Detect people
    results = model(center_frame)[0]
    person_boxes = [
        box.xyxy[0].cpu().numpy()
        for box in results.boxes
        if int(box.cls[0]) == 0
    ]
    print(f"[INFO] {len(person_boxes)} person(s) detected.")

    if len(person_boxes) == 0:
        return

    # Offset and clamp
    box_frames = {}
    adjusted_boxes = []
    for idx, box in enumerate(person_boxes):
        x1, y1, x2, y2 = box.astype(int)
        w, h = x2 - x1, y2 - y1
        dx, dy = int(w * offset_ratio), int(h * offset_ratio)
        x1, y1 = max(0, x1 - dx), max(0, y1 - dy)
        x2, y2 = min(width, x2 + dx), min(height, y2 + dy)
        if (x2-x1)%2!=0:
            x2-=1 
        if (y2-y1)%2!=0:
            y2-=1
        adjusted_boxes.append((x1, y1, x2, y2))
        box_frames[idx] = []

    # Extract and save frames
    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
    frame_idx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        for idx, (x1, y1, x2, y2) in enumerate(adjusted_boxes):
            crop = frame[y1:y2, x1:x2]
            box_frames[idx].append(np.array(crop))
        frame_idx += 1

    cap.release()

    # Convert to video via ffmpeg
    video_name = os.path.splitext(os.path.basename(video_path))[0]
    for idx in box_frames.keys():
        output_path = os.path.join(output_dir, f"{video_name}_person_{idx}.mp4")
        x1, y1, x2, y2 = adjusted_boxes[idx] 
        w, h = x2 - x1, y2 - y1
        
        cmd = [
            "ffmpeg", "-y",
            "-f", "rawvideo",
            "-vcodec", "rawvideo",
            "-pix_fmt", "rgb24",
            "-s", f"{w}x{h}",
            "-r", str(fps),
            "-i", "-",
            "-an",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-pix_fmt", "yuv420p",
            output_path
        ]
        
        process = subprocess.Popen(
            cmd, 
            stdin=subprocess.PIPE
        )
        for frame in box_frames[idx]:
            assert frame.dtype == np.uint8
            process.stdin.write(frame.tobytes())
        process.stdin.close()
        process.wait()


####################
##    Scene Detect #
####################

def extract_scenes_with_split(
    video_path: str,
    data_dir: str,
    threshold: float = 30.0,
    min_scene_len: int = 15
):
    filename = os.path.splitext(os.path.basename(video_path))[0]
    output_dir = os.path.join(data_dir, 'scene_segments', filename)
    os.makedirs(output_dir, exist_ok=True)

    video = open_video(video_path)

    # 씬 매니저 설정
    scene_manager = SceneManager()
    scene_manager.add_detector(ContentDetector(threshold=threshold, min_scene_len=min_scene_len))

    # 씬 감지 실행
    scene_manager.detect_scenes(video)
    scene_list = scene_manager.get_scene_list()

    print(f"[INFO] {len(scene_list)} scenes detected.")

    # FFMPEG로 분할 저장 (파일명 자동 지정: <input_basename>_Scene-001.mp4 형식)
    split_video_ffmpeg(
        input_video_path=video_path,
        scene_list=scene_list,
        output_dir=Path(output_dir),
        show_progress=True
    )
    return output_dir


if __name__ == "__main__":
    extract_person_clip_folder(
    "/Users/djyun/project/data_crawl/data/video/segments/RAW VIDEO Surveillance camera shows victim fight off armed suspects", 
    "/Users/djyun/project/data_crawl/data/video", 
    model_ckpt="yolov8n.pt",
    offset_ratio=0.2)