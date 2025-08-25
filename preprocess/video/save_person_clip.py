import os 
import cv2 
import numpy as np 
import subprocess 
from ultralytics import YOLO 
from tqdm import tqdm 
import shutil 

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

if __name__ == '__main__':
    test_video_path = "/Users/djyun/project/data_crawl/data/video/scene_split/[지금뉴스] 케데헌 만든 소니 “1조 벌었는데 수익은 270억”…이유가？ ⧸ KBS 2025.08.18.-Scene-031.mp4"
    output_dir = '/Users/djyun/project/data_crawl/data/video/person_clips'
    extract_person_clips(test_video_path, output_dir)