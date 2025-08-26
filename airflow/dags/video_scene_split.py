from airflow.decorators import dag, task 
from airflow.operators.python import get_current_context
from airflow.models.param import Param
from datetime import datetime, timedelta 
import os 
from glob import glob 

from pipeline_logic.video.crawler import download_video
from pipeline_logic.video.preprocess import extract_scenes_with_split, split_raw_to_segments_folder

@dag(
    dag_id="youtube_scene_detection",
    schedule=None,
    catchup=False,
    tags=["video", "youtube", "from_url", "scene_detect"],
    params={
        "url": Param("", type="string", description="YouTube URL"),
        "data_dir": Param("/data/video", type="string"),
        "resolution": Param("360", type="string"),
        "seg_duration": Param(5, type="integer"),
        "sample_rate": Param(5, type="integer"),
        "threshold": Param(30, type="number"),
        "min_scene_len": Param(15, type="integer")
    }
)
def youtube_scene_split():
    
    @task
    def prepare_args() -> dict:
        context = get_current_context()
        conf = context["dag_run"].conf
        return {
            "url": conf["url"], ## must 
            "data_dir": conf.get("data_dir", "/data/video"),
            "resolution": conf.get("resolution", "360"),
            "seg_duration": conf.get("seg_duration", 5),
            "sample_rate": conf.get("sample_rate", 5),
            "threshold": conf.get("threshold", 30),
            "min_scene_len": conf.get("min_scene_len", 15)
        }
    
    @task
    def download_from_youtube(args: dict) -> str: 
        ## crawl youtube video and save the raw video 
        return download_video(
            args["url"], args["data_dir"], 
            args["resolution"]
        )

    @task 
    def scene_split(video_path: str, args: dict) -> str: 
        return extract_scenes_with_split(
            video_path, args["data_dir"],
            args["threshold"], args["min_scene_len"]
        )
    
    @task
    def scene_to_segments(segment_path: str, args: dict) -> str: 
        return split_raw_to_segments_folder(
            segment_path, args["data_dir"],
            args["seg_duration"]
        )
    
    args = prepare_args()
    video_path = download_from_youtube(args)
    seg_folder = scene_split(video_path, args)
    _ = scene_to_segments(seg_folder, args)

youtube_scene_split = youtube_scene_split()