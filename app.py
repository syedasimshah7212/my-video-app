import streamlit as st
import yt_dlp
import subprocess
import os
import tempfile
import cv2
import numpy as np
from pathlib import Path

st.set_page_config(page_title="All-in-One AI Video Tool", layout="wide", page_icon="🎬")

st.title("🎬 All-in-One Video Tool (Prototype)")
st.caption("Simple interface • YouTube Cartoonize • Reference Style • Viral Shorts")

st.warning("⚠️ Prototype hai. YouTube download cloud pe kabhi-kabhi block hota hai (403). Upload option better hai. Real AI style ke liye API chahiye.")

TEMP_DIR = Path(tempfile.gettempdir()) / "video_tool"
TEMP_DIR.mkdir(exist_ok=True)

def download_youtube(url, output_path):
    ydl_opts = {
        'format': 'best[height<=720]/best',
        'outtmpl': str(output_path),
        'quiet': True,
        'no_warnings': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'web'],
                'skip': ['hls', 'dash']
            }
        },
        'retries': 3,
        'fragment_retries': 3,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return output_path.exists()
    except Exception as e:
        st.error(f"Download failed: {str(e)}")
        return False

def apply_cartoon_filter(input_path, output_path, max_frames=300):
    cap = cv2.VideoCapture(str(input_path))
    if not cap.isOpened():
        return False
    
    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))
    
    frame_count = 0
    progress = st.progress(0)
    status = st.empty()
    total_frames = min(int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or max_frames), max_frames)
    
    while cap.isOpened() and frame_count < max_frames:
        ret, frame = cap.read()
        if not ret:
            break
        
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.medianBlur(gray, 5)
        edges = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 9, 9)
        color = cv2.bilateralFilter(frame, 9, 250, 250)
        cartoon = cv2.bitwise_and(color, color, mask=edges)
        
        out.write(cartoon)
        frame_count += 1
        if frame_count % 8 == 0:
            progress.progress(min(frame_count / total_frames, 1.0))
            status.text(f"Processing... {frame_count}/{total_frames}")
    
    cap.release()
    out.release()
    progress.empty()
    status.empty()
    return frame_count > 0

def extract_shorts(input_path, output_dir, num_shorts=3, duration=15):
    shorts = []
    for i in range(num_shorts):
        start = i * 18
        out_path = output_dir / f"short_{i+1}.mp4"
        cmd = [
            "ffmpeg", "-y", "-i", str(input_path),
            "-ss", str(start), "-t", str(duration),
            "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
            "-c:a", "aac", "-b:a", "128k",
            str(out_path)
        ]
        try:
            subprocess.run(cmd, capture_output=True, timeout=45, check=False)
            if out_path.exists() and out_path.stat().st_size > 10000:
                shorts.append(out_path)
        except Exception:
            continue
    return shorts

# Tabs
tab1, tab2, tab3 = st.tabs(["🎨 Cartoonize Video", "🔄 Reference Style", "✂️ Viral Shorts"])

with tab1:
    st.header("Cartoonize / Style Transfer")
    st.info("YouTube link try karo (kabhi 403 aata hai). Better: video file upload karo.")
    
    col1, col2 = st.columns(2)
    with col1:
        yt_url = st.text_input("YouTube Link", placeholder="https://youtube.com/watch?v=...")
    with col2:
        uploaded = st.file_uploader("Ya video upload karo", type=["mp4", "mov", "avi", "mkv"])
    
    max_sec = st.slider("Max processing duration (seconds)", 5, 45, 20)
    
    if st.button("Process Video", type="primary", use_container_width=True):
        input_file = None
        if yt_url:
            with st.spinner("Downloading from YouTube..."):
                out_path = TEMP_DIR / "downloaded.mp4"
                if download_youtube(yt_url, out_path):
                    input_file = out_path
        elif uploaded is not None:
            input_file = TEMP_DIR / uploaded.name
            with open(input_file, "wb") as f:
                f.write(uploaded.getbuffer())
        
        if input_file and input_file.exists():
            output_file = TEMP_DIR / "cartoon_output.mp4"
            with st.spinner("Applying cartoon filter..."):
                success = apply_cartoon_filter(input_file, output_file, max_frames=int(max_sec * 25))
            
            if success and output_file.exists():
                st.success("Done! Cartoon video ready.")
                st.video(str(output_file))
                with open(output_file, "rb") as f:
                    st.download_button("Download Cartoon Video", f, file_name="cartoon_video.mp4")
                
                shorts = extract_shorts(output_file, TEMP_DIR, num_shorts=2)
                if shorts:
                    st.subheader("Auto Shorts")
                    for i, short in enumerate(shorts):
                        st.video(str(short))
                        with open(short, "rb") as f:
                            st.download_button(f"Download Short {i+1}", f, file_name=f"short_{i+1}.mp4", key=f"s{i}")
            else:
                st.error("Processing fail ho gaya.")
        else:
            st.error("Koi video nahi mili. Upload try karo.")

with tab2:
    st.header("Reference-Based Editor")
    st.info("Apni video upload karo. Reference abhi demo hai.")
    
    own_video = st.file_uploader("Apni Video", type=["mp4", "mov", "avi"], key="own")
    
    if st.button("Apply Style", type="primary") and own_video:
        input_file = TEMP_DIR / own_video.name
        with open(input_file, "wb") as f:
            f.write(own_video.getbuffer())
        
        output_file = TEMP_DIR / "ref_output.mp4"
        if apply_cartoon_filter(input_file, output_file, max_frames=150):
            st.video(str(output_file))
            with open(output_file, "rb") as f:
                st.download_button("Download Result", f, file_name="styled.mp4")

with tab3:
    st.header("Viral Shorts Extractor")
    long_video = st.file_uploader("Long Video Upload", type=["mp4", "mov", "avi"], key="long")
    num = st.slider("Number of shorts", 1, 4, 2)
    dur = st.slider("Duration (sec)", 8, 20, 12)
    
    if st.button("Extract Shorts", type="primary") and long_video:
        input_file = TEMP_DIR / long_video.name
        with open(input_file, "wb") as f:
            f.write(long_video.getbuffer())
        
        shorts = extract_shorts(input_file, TEMP_DIR, num_shorts=num, duration=dur)
        if shorts:
            st.success(f"{len(shorts)} shorts ready!")
            for i, short in enumerate(shorts):
                st.video(str(short))
                with open(short, "rb") as f:
                    st.download_button(f"Download Short {i+1}", f, file_name=f"viral_{i+1}.mp4", key=f"vs{i}")
        else:
            st.error("Shorts nahi bane. Video chhoti ho sakti hai.")

st.markdown("---")
st.caption("Prototype by Grok • YouTube cloud pe unstable hai, upload prefer karo.")