import os 
import subprocess
from glob import glob

def save_clip_with_sampling(data_folder, output_dir, sample_rate=5):
    video_name = data_folder.split('/')[-1]
    os.makedirs(os.path.join(output_dir, video_name), exist_ok=True)
    segment_paths = glob(os.path.join(data_folder, '*.mp4'))

    for s_path in segment_paths:
        filename = os.path.splitext(os.path.basename(s_path))[0]
        output_template = os.path.join(output_dir, video_name, f"{filename}_%03d.mp4")

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

if __name__ == "__main__":
    save_clip_with_sampling(
        data_folder="/Users/djyun/project/data_crawl/data/video/segments/“Golden” Official Lyric Video ｜ KPop Demon Hunters ｜ Sony Animation", 
        output_dir="/Users/djyun/project/data_crawl/data/video/train_clips",
        sample_rate=5    
    )