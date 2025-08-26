FROM apache/airflow:2.9.1-python3.10

USER root

# FFmpeg 설치 (apt 기반)
RUN apt-get update && apt-get install -y ffmpeg && apt-get clean

USER airflow

# requirements.txt 복사 및 설치
COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /requirements.txt