from airflow.decorators import dag, task 
from airflow.operators.python import get_current_context
from airflow.models.param import Param
from datetime import datetime, timedelta 
import os 
from glob import glob 

from pipeline_logic.video.crawler import download_video
from pipeline_logic.video.preprocess import extract_person_clip_folder, split_raw_to_segments_single

@dag(
    dag_id="youtube_person_clip",
    schedule=None,
    catchup=False,
    tags=["video", "youtube", "from_url", "person_detection"],
    params={
        "url": Param("", type="string", description="YouTube URL"),
        "data_dir": Param("/data/video", type="string"),
        "resolution": Param("360", type="string"),
        "seg_duration": Param(5, type="integer"),
        "sample_rate": Param(5, type="integer"),
        "model_ckpt": Param("yolov8n.pt", type="string"),
        "offset_ratio": Param(0.2, type="number")
    }
)
def youtube_person_clip():
    
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
            "model_ckpt": conf.get("model_ckpt", "yolov8n.pt"),
            "offset_ratio": conf.get("offset_ratio", 0.2)
        }
    
    @task
    def download_from_youtube(args: dict) -> str: 
        ## crawl youtube video and save the raw video 
        return download_video(
            args["url"], args["data_dir"], 
            args["resolution"]
        )
    
    @task
    def raw_to_segments(video_path: str, args: dict) -> str: 
        return split_raw_to_segments_single(
            video_path, args["data_dir"],
            args["seg_duration"]
        )
    
    @task 
    def make_person_clip(segment_path: str, args: dict) -> str: 
        extract_person_clip_folder(
            segment_path, args["data_dir"],
            args["model_ckpt"], args["offset_ratio"]
        )
    
    args = prepare_args()
    video_path = download_from_youtube(args)
    seg_folder = raw_to_segments(video_path, args)
    make_person_clip(seg_folder, args)

youtube_person_clip = youtube_person_clip()