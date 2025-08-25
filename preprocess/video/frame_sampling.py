import cv2
import os

def sample_frames_from_video(video_path, output_video_path, sampling_interval=5):
    # 비디오 캡처 객체 생성
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Can't open video: {video_path}")
    
    # 비디오 정보
    fps = cap.get(cv2.CAP_PROP_FPS)
    width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')

    # 출력 비디오 객체
    out = cv2.VideoWriter(output_video_path, fourcc, fps // sampling_interval, (width, height))

    frame_idx = 0
    sampled_count = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % sampling_interval == 0:
            out.write(frame)
            sampled_count += 1

        frame_idx += 1

    cap.release()
    out.release()
    print(f"✔ Saved {sampled_count} sampled frames to: {output_video_path}")