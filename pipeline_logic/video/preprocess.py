import os 
import subprocess 
from glob import glob 
import shutil 
from tqdm import tqdm
import cv2
from pathlib import Path

from scenedetect import SceneManager, open_video
from scenedetect.detectors import ContentDetector
from scenedetect.video_splitter import split_video_ffmpeg
from ultralytics import YOLO

####################
#  segment & clip  #
####################

def split_raw_to_segments(video_path, data_dir, seg_duration=5) -> str:
    filename = os.path.splitext(os.path.basename(video_path))[0]
    output_dir = os.path.join(data_dir, 'segments', filename)
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
def extract_person_clips(
    video_path,
    output_dir,
    model_ckpt="yolov8n.pt",
    offset_ratio=0.2
):
    os.makedirs(output_dir, exist_ok=True)

    model = YOLO(model_ckpt)

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
    adjusted_boxes = []
    for box in person_boxes:
        x1, y1, x2, y2 = box.astype(int)
        w, h = x2 - x1, y2 - y1
        dx, dy = int(w * offset_ratio), int(h * offset_ratio)
        x1, y1 = max(0, x1 - dx), max(0, y1 - dy)
        x2, y2 = min(width, x2 + dx), min(height, y2 + dy)
        adjusted_boxes.append((x1, y1, x2, y2))

    # Prepare temp dirs
    temp_root = os.path.join(output_dir, "_temp")
    if os.path.exists(temp_root):
        shutil.rmtree(temp_root)
    os.makedirs(temp_root)

    temp_dirs = []
    for i in range(len(adjusted_boxes)):
        td = os.path.join(temp_root, f"person_{i}")
        os.makedirs(td)
        temp_dirs.append(td)

    # Extract and save frames
    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
    frame_idx = 0
    with tqdm(total=total_frames, desc="Cropping frames") as pbar:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            for i, (x1, y1, x2, y2) in enumerate(adjusted_boxes):
                crop = frame[y1:y2, x1:x2]
                out_path = os.path.join(temp_dirs[i], f"frame_{frame_idx:05d}.jpg")
                cv2.imwrite(out_path, crop)
            frame_idx += 1
            pbar.update(1)

    cap.release()

    # Convert to video via ffmpeg
    for i, temp_dir in enumerate(temp_dirs):
        output_path = os.path.join(output_dir, f"person_{i}.mp4")
        ffmpeg_cmd = [
            "ffmpeg", "-y",
            "-framerate", "30",
            "-i", f"{temp_dir}/frame_%05d.jpg",
            "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-crf", "23",
            str(output_path)
        ]
        subprocess.run(ffmpeg_cmd, check=True)
        print(f"[SAVED] {output_path}")

    shutil.rmtree(temp_root)
    print("[DONE] All person clips saved.")



####################
##    Scene Detect #
####################

def extract_scenes_with_split(
    input_path: str,
    output_dir: str,
    threshold: float = 30.0,
    min_scene_len: int = 15
):
    os.makedirs(output_dir, exist_ok=True)
    video = open_video(input_path)

    # 씬 매니저 설정
    scene_manager = SceneManager()
    scene_manager.add_detector(ContentDetector(threshold=threshold, min_scene_len=min_scene_len))

    # 씬 감지 실행
    scene_manager.detect_scenes(video)
    scene_list = scene_manager.get_scene_list()

    print(f"[INFO] {len(scene_list)} scenes detected.")

    # FFMPEG로 분할 저장 (파일명 자동 지정: <input_basename>_Scene-001.mp4 형식)
    split_video_ffmpeg(
        input_video_path=input_path,
        scene_list=scene_list,
        output_dir=Path(output_dir),
        show_progress=True
    )