from airflow.decorators import dag, task
from airflow.utils.dates import days_ago
import glob

@dag(schedule_interval=None, start_date=days_ago(1), catchup=False)
def video_preprocessing_pipeline():

    @task
    def download_youtube(url: str) -> str:
        return download_youtube_video(url, "/videos")

    @task
    def split_into_clips(video_path: str) -> list:
        return split_video_into_clips(video_path, "/clips")

    @task
    def get_all_clips() -> list:
        return glob.glob("/clips/**/*.mp4", recursive=True)

    @task
    def preprocess(clip_path: str):
        preprocess_clip(clip_path, "/processed")

    url = "https://youtube.com/your_url_here"
    video_path = download_youtube(url)
    split_into_clips(video_path)
    clip_list = get_all_clips()
    preprocess.expand(clip_path=clip_list)

video_preprocessing_pipeline()