import os 
import subprocess 

def split_raw_to_segments(video_path, output_dir, clip_duration=5):
    filename = os.path.splitext(os.path.basename(video_path))[0]
    os.makedirs(os.path.join(output_dir, filename), exist_ok=True)
    output_template = os.path.join(output_dir, filename, "%03d.mp4")

    command = [
        "ffmpeg",
        "-i", video_path,
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-force_key_frames", f"expr:gte(t,n_forced*{clip_duration})",
        "-segment_time", str(clip_duration),
        "-f", "segment",
        "-reset_timestamps", "1",
        output_template
    ]
    subprocess.run(command, check=True)

if __name__ == "__main__":
    test_video_path = "/Users/djyun/project/data_crawl/data/video/raw/“Golden” Official Lyric Video ｜ KPop Demon Hunters ｜ Sony Animation.mp4"
    output_dir = '/Users/djyun/project/data_crawl/data/video/segments'
    split_raw_to_segments(test_video_path, output_dir)