from airflow.decorators import dag, task 
from airflow.operators.python import get_current_context
from airflow.models.param import Param
from datetime import datetime, timedelta 
import os 
from glob import glob 

from pipeline_logic.video.crawler import download_video
from pipeline_logic.video.preprocess import split_raw_to_segments, save_clip_with_sampling

@dag(
    dag_id="youtube_video_crawling_pipeline",
    schedule=None,
    catchup=False,
    tags=["video", "youtube", "from_url"],
    params={
        "url": Param("", type="string", description="YouTube URL"),
        "data_dir": Param("/data/video", type="string"),
        "resolution": Param("360", type="string"),
        "seg_duration": Param(5, type="integer"),
        "sample_rate": Param(5, type="integer")
    }
)
def basic_youtube_crawl():
    
    @task 
    def prepare_args() -> dict:
        context = get_current_context()
        conf = context["dag_run"].conf
        return {
            "url": conf["url"], ## must 
            "data_dir": conf.get("data_dir", "/data/video"),
            "resolution": conf.get("resolution", "360"),
            "seg_duration": conf.get("seg_duration", 5),
            "sample_rate": conf.get("sample_rate", 5)
        }
    
    @task
    def download_from_youtube(args: dict) -> str: 
        ## crawl youtube video and save the raw video 
        return download_video(
            args["url"], args["data_dir"], 
            args["resolution"]
        )
    
    @task 
    def raw_to_segment(video_path: str, args: dict) -> str:
        return split_raw_to_segments(
            video_path, args["data_dir"],
            args["seg_duration"]
        )
    
    @task 
    def segment_to_clip(segment_path: str, args: dict) -> str:
        return save_clip_with_sampling(
            segment_path, args["data_dir"], 
            args["sample_rate"]
        )
    
    args = prepare_args()
    video_path = download_from_youtube(args)
    segment_path = raw_to_segment(video_path, args)
    segment_to_clip(segment_path, args)
    
basic_youtube_crawl = basic_youtube_crawl()