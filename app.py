import streamlit as st
import yt_dlp
import subprocess
import os
import tempfile
import cv2
import numpy as np
from pathlib import Path
import time

st.set_page_config(page_title="All-in-One AI Video Tool", layout="wide", page_icon="🎬")

st.title("🎬 All-in-One Video Tool (Prototype)")
st.caption("Simple interface • YouTube Cartoonize • Reference Style • Viral Shorts")

st.warning("⚠️ This is a working prototype. Full high-quality AI cartoonization of long videos requires external APIs (DomoAI, Runway, etc.) and takes time. Local processing here uses OpenCV filters and FFmpeg. Copyright: Use only your own content or content you have rights to.")

# Create temp directory
TEMP_DIR = Path(tempfile.gettempdir()) / "video_tool"
TEMP_DIR.mkdir(exist_ok=True)

def download_youtube(url, output_path):
    ydl_opts = {
        'format': 'bestvideo[height<=720]+bestaudio/best[height<=720]/best',
        'outtmpl': str(output_path),
        'quiet': True,
        'no_warnings': True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return True
    except Exception as e:
        st.error(f"Download failed: {e}")
        return False

def apply_cartoon_filter(input_path, output_path, max_frames=300):
    """Simple OpenCV cartoon filter (for demo - slow on long videos)"""
    cap = cv2.VideoCapture(str(input_path))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))
    
    frame_count = 0
    progress = st.progress(0)
    status = st.empty()
    
    total_frames = min(int(cap.get(cv2.CAP_PROP_FRAME_COUNT)), max_frames)
    
    while cap.isOpened() and frame_count < max_frames:
        ret, frame = cap.read()
        if not ret:
            break
        
        # Cartoon filter
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.medianBlur(gray, 5)
        edges = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 9, 9)
        color = cv2.bilateralFilter(frame, 9, 300, 300)
        cartoon = cv2.bitwise_and(color, color, mask=edges)
        
        out.write(cartoon)
        frame_count += 1
        if frame_count % 10 == 0:
            progress.progress(min(frame_count / total_frames, 1.0))
            status.text(f"Processing frame {frame_count}/{total_frames}")
    
    cap.release()
    out.release()
    progress.empty()
    status.empty()
    return frame_count > 0

def extract_shorts(input_path, output_dir, num_shorts=3, duration=15):
    """Extract short clips using FFmpeg"""
    shorts = []
    for i in range(num_shorts):
        start = i * 20  # simple spacing
        out_path = output_dir / f"short_{i+1}.mp4"
        cmd = [
            "ffmpeg", "-y", "-i", str(input_path),
            "-ss", str(start), "-t", str(duration),
            "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920",
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-c:a", "aac", str(out_path)
        ]
        try:
            subprocess.run(cmd, capture_output=True, timeout=60)
            if out_path.exists():
                shorts.append(out_path)
        except Exception:
            pass
    return shorts

# Tabs
tab1, tab2, tab3 = st.tabs(["🎨 Cartoonize Video", "🔄 Reference Style", "✂️ Viral Shorts"])

with tab1:
    st.header("Cartoonize / Style Transfer")
    st.info("YouTube link ya video upload karo. Local cartoon filter apply hoga (demo). Full AI ke liye API connect karna hoga.")
    
    col1, col2 = st.columns(2)
    with col1:
        yt_url = st.text_input("YouTube Link", placeholder="https://youtube.com/watch?v=...")
    with col2:
        uploaded = st.file_uploader("Ya video upload karo", type=["mp4", "mov", "avi"])
    
    style = st.selectbox("Style", ["Cartoon (OpenCV)", "Anime-like (placeholder)", "3D Cartoon (placeholder)"])
    max_sec = st.slider("Max processing duration (seconds)", 10, 60, 30)
    
    if st.button("Process Video", type="primary", use_container_width=True):
        input_file = None
        if yt_url:
            with st.spinner("Downloading from YouTube..."):
                out_path = TEMP_DIR / "downloaded.mp4"
                if download_youtube(yt_url, out_path):
                    input_file = out_path
        elif uploaded:
            input_file = TEMP_DIR / uploaded.name
            with open(input_file, "wb") as f:
                f.write(uploaded.getbuffer())
        
        if input_file and input_file.exists():
            output_file = TEMP_DIR / "cartoon_output.mp4"
            with st.spinner("Applying cartoon filter..."):
                success = apply_cartoon_filter(input_file, output_file, max_frames=max_sec*25)
            
            if success and output_file.exists():
                st.success("Done! Cartoon video ready.")
                st.video(str(output_file))
                with open(output_file, "rb") as f:
                    st.download_button("Download Cartoon Video", f, file_name="cartoon_video.mp4")
                
                # Also generate shorts
                shorts = extract_shorts(output_file, TEMP_DIR)
                if shorts:
                    st.subheader("Auto Shorts")
                    for i, short in enumerate(shorts):
                        st.video(str(short))
                        with open(short, "rb") as f:
                            st.download_button(f"Download Short {i+1}", f, file_name=f"short_{i+1}.mp4", key=f"s{i}")
        else:
            st.error("Koi video nahi mili.")

with tab2:
    st.header("Reference-Based Editor")
    st.info("Apni video left pe, reference right pe. Prototype mein simple filter apply hoga. Real style transfer ke liye API chahiye.")
    
    col1, col2 = st.columns(2)
    with col1:
        own_video = st.file_uploader("Apni Video", type=["mp4", "mov"], key="own")
    with col2:
        ref_video = st.file_uploader("Reference Video / Image", type=["mp4", "mov", "jpg", "png"], key="ref")
    
    if st.button("Apply Reference Style", type="primary"):
        if own_video:
            st.info("Prototype mode: Applying enhanced cartoon filter as demo. Full reference style transfer needs AI API integration.")
            # Reuse cartoon for demo
            input_file = TEMP_DIR / own_video.name
            with open(input_file, "wb") as f:
                f.write(own_video.getbuffer())
            output_file = TEMP_DIR / "ref_output.mp4"
            apply_cartoon_filter(input_file, output_file, max_frames=200)
            if output_file.exists():
                st.video(str(output_file))
                with open(output_file, "rb") as f:
                    st.download_button("Download Result", f, file_name="reference_styled.mp4")
        else:
            st.warning("Apni video upload karo.")

with tab3:
    st.header("Viral Shorts Extractor")
    st.info("Long video se short vertical clips nikaalo with simple cropping.")
    
    long_video = st.file_uploader("Long Video Upload", type=["mp4", "mov"], key="long")
    num = st.slider("Number of shorts", 1, 5, 3)
    dur = st.slider("Duration of each short (sec)", 10, 30, 15)
    
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
                    st.download_button(f"Download Short {i+1}", f, file_name=f"viral_short_{i+1}.mp4", key=f"vs{i}")
        else:
            st.error("Shorts extract nahi ho sake.")

st.markdown("---")
st.caption("Built as a prototype by Grok. To add real AI style transfer, connect DomoAI / Runway / other APIs in the processing functions. Run with: streamlit run app.py")
def download_youtube(url, output_path):
    ydl_opts = {
        'format': 'best[height<=720]/best',  # single format, no merge needed
        'outtmpl': str(output_path),
        'quiet': True,
        'no_warnings': True,
        'merge_output_format': 'mp4',
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return True
    except Exception as e:
        st.error(f"Download failed: {e}")
        return False
