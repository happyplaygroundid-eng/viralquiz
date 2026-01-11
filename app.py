import streamlit as st
import PIL.Image, PIL.ImageFont, PIL.ImageDraw
import os
import re
import random
import asyncio
import tempfile
import numpy as np
import pandas as pd
import textwrap
from io import StringIO

# FIX COMPATIBILITY PILLOW
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = getattr(PIL.Image, 'LANCZOS', PIL.Image.BICUBIC)

# IMPORT MOVIEPY V2.0+ (MODULAR WAY - PASTI JALAN DI PYTHON 3.13)
from moviepy.video.io.VideoFileClip import VideoFileClip
from moviepy.audio.io.AudioFileClip import AudioFileClip
from moviepy.video.VideoClip import ImageClip
from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip
from moviepy.audio.AudioClip import CompositeAudioClip

import edge_tts

st.set_page_config(page_title="Viral Shorts Factory", layout="wide")
st.title("💀 Viral Shorts Factory (V2.0 STABLE)")

# --- DATABASE ---
HOOK_DB = {
    "Ego Challenge": [f"Only {random.randint(1,5)}% can solve this." for _ in range(50)],
    "Curiosity Shock": ["This feels illegal to know.", "Your brain is lying to you."] * 50,
    "Time Pressure": ["Quick! 5 seconds only.", "Decide before the timer ends!"] * 50
}
STAY_DB = {
    "Warning": ["Don't answer too fast.", "Stop scrolling right now."] * 50,
    "Tease": ["The twist is at the end.", "You won't believe the answer."] * 50,
    "Doubt": ["You're probably wrong.", "Are you absolutely sure?"] * 50
}

# --- SIDEBAR ---
with st.sidebar:
    st.header("🎙️ 1. Suara (US Native)")
    voice_choice = st.radio("Pilih Suara:", ["Male (Christopher)", "Female (Aria)"])
    voice_id = "en-US-ChristopherNeural" if "Male" in voice_choice else "en-US-AriaNeural"
    st.write("---")
    st.header("📤 Assets")
    bg_video = st.file_uploader("Upload Background Video", type=["mp4"])
    backsound = st.file_uploader("Upload Backsound", type=["mp3"])
    timer_sfx = st.file_uploader("Upload Timer SFX", type=["mp3"])
    font_file = st.file_uploader("Upload Font (.ttf)", type=["ttf"])

# --- INTERFACE ---
st.header("📝 Data Kuis Masal (Bulk)")
quiz_csv = st.text_area("Paste CSV (Format: Pertanyaan,Jawaban)", height=150)
download_placeholder = st.empty()

selected_row = None
if quiz_csv:
    try:
        df = pd.read_csv(StringIO(quiz_csv), names=["Pertanyaan", "Jawaban"])
        df.index = df.index + 1
        q_number = st.selectbox("🎯 Render Pertanyaan Nomor:", df.index)
        selected_row = df.loc[q_number]
    except Exception as e:
        st.error(f"Format CSV bermasalah: {e}")

col_h, col_s = st.columns(2)
with col_h: hook_type = st.selectbox("🪝 Pilih Hook", list(HOOK_DB.keys()))
with col_s: stay_type = st.selectbox("🛑 Pilih Stay Line", list(STAY_DB.keys()))

async def generate_voice(text, filename, v_id):
    communicate = edge_tts.Communicate(text, v_id, rate="-5%", volume="+20%")
    await communicate.save(filename)

def make_text_clip(text, font_path, fontsize, duration, start_time, color='white', bg_color=(0,0,0,180)):
    W, H = 1080, 450
    img = PIL.Image.new('RGBA', (W, H), (0, 0, 0, 0))
    draw = PIL.ImageDraw.Draw(img)
    try: font = PIL.ImageFont.truetype(font_path, fontsize)
    except: font = PIL.ImageFont.load_default()
    wrapped = textwrap.fill(text, width=22)
    l, t, r, b = draw.multiline_textbbox((0, 0), wrapped, font=font, align='center')
    tx, ty = (W-(r-l))/2, (H-(b-t))/2
    draw.rectangle([tx-25, ty-25, tx+(r-l)+25, ty+(b-t)+25], fill=bg_color)
    draw.multiline_text((tx, ty), wrapped, font=font, fill=color, align='center')
    # SINTAKS BARU: with_start & with_duration
    return ImageClip(np.array(img)).with_start(start_time).with_duration(duration).with_position(('center', 'center'))

if st.button("🚀 MULAI GENERATE VIDEO", use_container_width=True):
    if not bg_video or not font_file or selected_row is None:
        st.error("Bahan belum lengkap!")
    else:
        with st.spinner("Rendering..."):
            try:
                tmp_dir = tempfile.gettempdir()
                f_font = os.path.join(tmp_dir, "f.ttf")
                with open(f_font, "wb") as f: f.write(font_file.read())
                
                pertanyaan = selected_row['Pertanyaan']
                jawaban = selected_row['Jawaban']
                
                # 1. Voice
                v_file = os.path.join(tmp_dir, "v.mp3")
                script = f"{random.choice(HOOK_DB[hook_type])}. {random.choice(STAY_DB[stay_type])}. {pertanyaan}. {jawaban}. Watch again."
                asyncio.run(generate_voice(script, v_file, voice_id))
                
                # 2. Background Video (SINTAKS BARU: .cut menggantikan .subclip)
                bg_path = os.path.join(tmp_dir, "b.mp4")
                with open(bg_path, "wb") as f: f.write(bg_video.read())
                
                clip_bg = VideoFileClip(bg_path).cut(0, 26).resized(height=1920).crop(x_center=540, width=1080, height=1920)
                
                # 3. Layers
                c1 = make_text_clip(random.choice(HOOK_DB[hook_type]), f_font, 95, 2, 0)
                c2 = make_text_clip(random.choice(STAY_DB[stay_type]), f_font, 85, 3, 2, color='yellow')
                c3 = make_text_clip(pertanyaan, f_font, 80, 6, 5)
                c4 = make_text_clip("3... 2... 1...", f_font, 130, 5, 11)
                c5 = make_text_clip(jawaban, f_font, 100, 6, 16, color='lime')
                c6 = make_text_clip("DID YOU GET IT?\nWatch Again", f_font, 75, 4, 22)

                # 4. Audio Mixing (SINTAKS BARU: with_start, with_duration, with_audio)
                audio_clips = [AudioFileClip(v_file)]
                if backsound:
                    m_p = os.path.join(tmp_dir, "m.mp3")
                    with open(m_p, "wb") as f: f.write(backsound.read())
                    audio_clips.append(AudioFileClip(m_p).multiply_volume(0.3).with_duration(26))
                
                if timer_sfx:
                    s_p = os.path.join(tmp_dir, "s.mp3")
                    with open(s_p, "wb") as f: f.write(timer_sfx.read())
                    audio_clips.append(AudioFileClip(s_p).with_start(11).with_duration(5))
                
                final_audio = CompositeAudioClip(audio_clips).with_duration(26)
                final_video = CompositeVideoClip([clip_bg, c1, c2, c3, c4, c5, c6]).with_audio(final_audio)
                
                # 5. Export
                out_file = os.path.join(tmp_dir, "final.mp4")
                final_video.write_videofile(out_file, codec="libx264", audio_codec="aac", fps=24, preset="ultrafast", ffmpeg_params=["-pix_fmt", "yuv420p"])
                
                with open(out_file, "rb") as f:
                    v_bytes = f.read()
                
                clean_name = re.sub(r'[^\w\s-]', '', pertanyaan).strip().lower()
                clean_name = re.sub(r'[-\s]+', '_', clean_name)[:50] + ".mp4"
                
                download_placeholder.download_button(label=f"📥 DOWNLOAD: {clean_name}", data=v_bytes, file_name=clean_name, mime="video/mp4", type="primary", use_container_width=True)
                st.video(v_bytes)
                
            except Exception as e:
                st.error(f"Render Gagal Total: {e}")
