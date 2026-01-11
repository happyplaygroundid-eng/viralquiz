import streamlit as st
import PIL.Image
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

# FIX IMPORT MOVIEPY UNIVERSAL
try:
    from moviepy.editor import VideoFileClip, AudioFileClip, ImageClip, CompositeVideoClip, CompositeAudioClip
except ImportError:
    from moviepy.video.io.VideoFileClip import VideoFileClip
    from moviepy.audio.io.AudioFileClip import AudioFileClip
    from moviepy.video.VideoClip import ImageClip
    from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip
    from moviepy.audio.AudioClip import CompositeAudioClip

import edge_tts

st.set_page_config(page_title="Shorts Bulk Factory", layout="wide")
st.title("💀 Shorts Bulk Factory (V3.0)")

# --- DATABASE HOOKS & STAY LINES ---
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
    st.header("🎙️ 1. Voice Config")
    voice_choice = st.radio("Voice:", ["Male (Christopher)", "Female (Aria)"])
    voice_id = "en-US-ChristopherNeural" if "Male" in voice_choice else "en-US-AriaNeural"

    st.write("---")
    st.header("📤 Assets")
    bg_video = st.file_uploader("BG Video", type=["mp4"])
    backsound = st.file_uploader("Backsound", type=["mp3"])
    font_file = st.file_uploader("Font (.ttf)", type=["ttf"])

# --- MAIN INTERFACE ---
st.header("📝 Bulk Quiz Data")
quiz_csv = st.text_area("Paste CSV (Format: Pertanyaan,Jawaban)", height=150, placeholder="Who is...?,The King!\nWhat is...?,A Shadow!")

# Area Download di Atas
download_placeholder = st.empty()

# Logika Pilih Nomor Pertanyaan
selected_row = None
if quiz_csv:
    try:
        df = pd.read_csv(StringIO(quiz_csv), names=["Pertanyaan", "Jawaban"])
        df.index = df.index + 1 # Nomor mulai dari 1
        st.write("### List Pertanyaan yang Terdeteksi:")
        st.dataframe(df, use_container_width=True)
        
        q_number = st.selectbox("🎯 Pilih Nomor Pertanyaan untuk di-Render:", df.index)
        selected_row = df.loc[q_number]
    except Exception as e:
        st.error(f"Format CSV salah: {e}")

col_h, col_s = st.columns(2)
with col_h: hook_type = st.selectbox("🪝 Pilih Hook", list(HOOK_DB.keys()))
with col_s: stay_type = st.selectbox("🛑 Pilih Stay Line", list(STAY_DB.keys()))

# --- FUNCTIONS ---
async def generate_voice(text, filename, v_id):
    communicate = edge_tts.Communicate(text, v_id, rate="-5%", volume="+20%")
    await communicate.save(filename)

def make_text_clip(text, font_path, fontsize, duration, start_time, color='white', bg_color=(0,0,0,180)):
    W, H = 1080, 450
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    try: font = ImageFont.truetype(font_path, fontsize)
    except: font = ImageFont.load_default()
    
    wrapped = textwrap.fill(text, width=22)
    l, t, r, b = draw.multiline_textbbox((0, 0), wrapped, font=font, align='center')
    tx, ty = (W-(r-l))/2, (H-(b-t))/2
    draw.rectangle([tx-25, ty-25, tx+(r-l)+25, ty+(b-t)+25], fill=bg_color)
    draw.multiline_text((tx, ty), wrapped, font=font, fill=color, align='center')
    return ImageClip(np.array(img)).set_start(start_time).set_duration(duration).set_position(('center', 'center'))

def slugify(text):
    """Membersihkan nama file dari karakter aneh"""
    text = re.sub(r'[^\w\s-]', '', text).strip().lower()
    return re.sub(r'[-\s]+', '_', text)[:50] # Limit 50 karakter

# --- EXECUTION ---
if st.button("🚀 GENERATE VIDEO SEKARANG", use_container_width=True):
    if not bg_video or not font_file or selected_row is None:
        st.error("Lengkapi data dan pilih pertanyaan dulu!")
    else:
        with st.spinner(f"Rendering Pertanyaan #{q_number}..."):
            try:
                tmp_dir = "/tmp" if os.path.exists("/tmp") else tempfile.gettempdir()
                f_font = os.path.join(tmp_dir, "f.ttf")
                with open(f_font, "wb") as f: f.write(font_file.read())
                
                sel_hook = random.choice(HOOK_DB[hook_type])
                sel_stay = random.choice(STAY_DB[stay_type])
                pertanyaan = selected_row['Pertanyaan']
                jawaban = selected_row['Jawaban']
                
                # Nama File dari Pertanyaan
                clean_name = slugify(pertanyaan) + ".mp4"
                
                # Audio
                v_file = os.path.join(tmp_dir, "v.mp3")
                script = f"{sel_hook}. {sel_stay}. {pertanyaan}. {jawaban}. Watch again."
                asyncio.run(generate_voice(script, v_file, voice_id))
                
                # Video Base
                bg_path = os.path.join(tmp_dir, "b.mp4")
                with open(bg_path, "wb") as f: f.write(bg_video.read())
                clip_bg = VideoFileClip(bg_path).subclip(0, 26).resize(height=1920).crop(x_center=540, width=1080, height=1920)
                
                # Text Clips
                c1 = make_text_clip(sel_hook, f_font, 95, 2, 0)
                c2 = make_text_clip(sel_stay, f_font, 85, 3, 2, color='yellow')
                c3 = make_text_clip(pertanyaan, f_font, 80, 6, 5)
                c4 = make_text_clip("3... 2... 1...", f_font, 130, 5, 11)
                c5 = make_text_clip(jawaban, f_font, 100, 6, 16, color='lime')
                c6 = make_text_clip("DID YOU GET IT?\nWatch Again", f_font, 75, 4, 22)

                final_video = CompositeVideoClip([clip_bg, c1, c2, c3, c4, c5, c6])
                
                # Audio Mix
                audio_clips = [AudioFileClip(v_file)]
                if backsound:
                    m_p = os.path.join(tmp_dir, "m.mp3")
                    with open(m_p, "wb") as f: f.write(backsound.read())
                    audio_clips.append(AudioFileClip(m_p).volumex(0.3).set_duration(26))
                
                final_video = final_video.set_audio(CompositeAudioClip(audio_clips).set_duration(26))
                
                # Render
                out_file = os.path.join(tmp_dir, "final.mp4")
                final_video.write_videofile(out_file, codec="libx264", audio_codec="aac", fps=24, preset="ultrafast", ffmpeg_params=["-pix_fmt", "yuv420p"])
                
                with open(out_file, "rb") as f:
                    v_bytes = f.read()
                
                # Tampilkan Download Button di Atas (Placeholder)
                st.success(f"✅ Render Selesai: {clean_name}")
                download_placeholder.download_button(
                    label=f"📥 DOWNLOAD: {clean_name}", 
                    data=v_bytes, 
                    file_name=clean_name, 
                    mime="video/mp4",
                    type="primary",
                    use_container_width=True
                )
                
                st.video(v_bytes)
                
            except Exception as e:
                st.error(f"Error: {e}")
