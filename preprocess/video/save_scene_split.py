import os 
import subprocess
from pathlib import Path

from scenedetect import SceneManager, open_video
from scenedetect.detectors import ContentDetector
from scenedetect.video_splitter import split_video_ffmpeg

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

if __name__ == "__main__":
    # test_video_path = "/Users/djyun/project/data_crawl/examples/youtube_output/“Golden” Official Lyric Video ｜ KPop Demon Hunters ｜ Sony Animation.mp4"
    test_video_path = '/Users/djyun/project/data_crawl/examples/youtube_output/[지금뉴스] 케데헌 만든 소니 “1조 벌었는데 수익은 270억”…이유가？ ⧸ KBS 2025.08.18..mp4'
    output_dir = '/Users/djyun/project/data_crawl/data/video/scene_split'
    # split_video_by_scenes(test_video_path, output_dir)

    extract_scenes_with_split(test_video_path, output_dir)