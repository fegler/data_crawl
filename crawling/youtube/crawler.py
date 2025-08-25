import os 
import json 
import subprocess 

from googleapiclient.discovery import build 
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env")
API_KEY = os.getenv("YOUTUBE_API_KEY")
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"

def search_youtube_videos(query, max_results=5):
    youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, developerKey=API_KEY)

    search_response = youtube.search().list(
        q=query,
        part="id, snippet",
        maxResults=max_results,
        type="video"
    ).execute()

    video_infos = [] 
    for item in search_response.get('items', []):
        video_id = item["id"]["videoId"]
        snippet = item["snippet"]

        video_infos.append({
            'id': video_id,
            'title': snippet['title'],
            'channel': snippet['channelTitle'],
            'publishedAt': snippet['publishedAt'],
            'description': snippet['description'],
            'url': f"http://www.youtube.com/watch?v={video_id}"
        })

    return video_infos

def download_video(url, output_dir, resolution='360'):
    ## using YouTube-dlp
    command = [
        "yt-dlp",
        "-f", f"bestvide[height<={resolution}]+bestaudio/best",
        "-o", os.path.join(output_dir, "%(title).70s.%(ext)s"),
        url
    ]
    subprocess.run(command)

def save_metadata(video_infos, output_path):
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(video_infos, f, ensure_ascii='False', indent=2)


if __name__ == '__main__':
    query = '케데헌 골든'
    output_dir = './examples/youtube_output'
    os.makedirs(output_dir, exist_ok=True)

    print(f"[+] Searching for YouTube videos with query: {query}")
    videos = search_youtube_videos(query)
    
    print(f"[+] Found {len(videos)} videos. Downloading...")
    for v in videos:
        download_video(v['url'], output_dir)
    
    save_metadata(videos, os.path.join(output_dir, 'metadata.json'))
    print("[+] Done.")