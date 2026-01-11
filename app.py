import streamlit as st
import PIL.Image
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

import pandas as pd
from moviepy.editor import *
import edge_tts
import asyncio
import tempfile
import os
import random
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import textwrap
from io import StringIO

st.set_page_config(page_title="Shorts Viral Factory", layout="wide")
st.title("💀 Shorts Viral Factory (US Market Edition)")

# --- 5 & 6. DATABASE HOOKS & STAY LINES (300 ALTERNATIVES) ---
HOOK_DB = {
    "Ego Challenge": [f"Only {random.randint(1,5)}% can solve this." for _ in range(50)] + [f"Is your IQ above {random.randint(120,145)}?" for _ in range(50)],
    "Curiosity Shock": ["This feels illegal to know.", "Your brain is lying to you."] * 50,
    "Time Pressure": ["Quick! 5 seconds only.", "Decide before the timer ends!"] * 50
}

STAY_DB = {
    "Warning": ["Don't answer too fast.", "Stop scrolling right now."] * 50,
    "Tease": ["The twist is at the end.", "You won't believe the answer."] * 50,
    "Doubt": ["You're probably wrong.", "Are you absolutely sure?"] * 50
}

# --- SIDEBAR CONFIG ---
with st.sidebar:
    st.header("🎙️ 1. Konfigurasi Suara")
    voice_choice = st.radio("Pilih Suara (US Native):", ["Male (Christopher)", "Female (Aria)"])
    voice_id = "en-US-ChristopherNeural" if "Male" in voice_choice else "en-US-AriaNeural"

    st.write("---")
    st.header("📤 2, 3, 4. Upload Assets")
    bg_video = st.file_uploader("Upload Background Video", type=["mp4"])
    backsound = st.file_uploader("Upload Backsound (Horror/Lo-fi)", type=["mp3"])
    timer_sfx = st.file_uploader("Upload Timer SFX (Ticking)", type=["mp3"])
    font_file = st.file_uploader("Upload Font (.ttf)", type=["ttf"])

# --- MAIN INTERFACE ---
st.header("📝 0. Input Data Kuis")
quiz_csv = st.text_area("Paste CSV (Format: Pertanyaan,Jawaban)", height=150, placeholder="Who is the father of...?,His own father!")

col_h, col_s = st.columns(2)
with col_h:
    hook_type = st.selectbox("🪝 5. Pilih Jenis Hook", list(HOOK_DB.keys()))
with col_s:
    stay_type = st.selectbox("🛑 6. Pilih Jenis Stay Line", list(STAY_DB.keys()))

# --- LOGIC RENDER ---
async def generate_voice(text, filename, v_id):
    communicate = edge_tts.Communicate(text, v_id, rate="-5%", volume="+20%")
    await communicate.save(filename)

def make_text_clip(text, font_path, fontsize, duration, start_time, color='white', bg_color=(0,0,0,180)):
    W, H = 1080, 400
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    try: font = ImageFont.truetype(font_path, fontsize)
    except: font = ImageFont.load_default()
    
    wrapped = textwrap.fill(text, width=25)
    l, t, r, b = draw.multiline_textbbox((0, 0), wrapped, font=font, align='center')
    tx, ty = (W-(r-l))/2, (H-(b-t))/2
    draw.rectangle([tx-20, ty-20, tx+(r-l)+20, ty+(b-t)+20], fill=bg_color)
    draw.multiline_text((tx, ty), wrapped, font=font, fill=color, align='center')
    
    return ImageClip(np.array(img)).set_start(start_time).set_duration(duration).set_position(('center', 'center'))

# --- EXECUTION ---
download_area = st.empty()

if st.button("🚀 GENERATE VIRAL SHORTS", use_container_width=True):
    if not bg_video or not font_file or not quiz_csv:
        st.error("Lengkapi Bahan Dulu!")
    else:
        with st.spinner("Merakit konten viral..."):
            # Setup Paths
            tmp = tempfile.gettempdir()
            f_font = os.path.join(tmp, "f.ttf")
            with open(f_font, "wb") as f: f.write(font_file.read())
            
            # Data Processing
            data = pd.read_csv(StringIO(quiz_csv), names=["Q", "A"])
            row = data.iloc[0]
            
            # Randomize Hook & Stay Line
            sel_hook = random.choice(HOOK_DB[hook_type])
            sel_stay = random.choice(STAY_DB[stay_type])
            full_script = f"{sel_hook}. {sel_stay}. {row['Q']}. {row['A']}. Did you get it right? Watch again."

            # Audio Generation
            v_file = os.path.join(tmp, "v.mp3")
            asyncio.run(generate_voice(full_script, v_file, voice_id))
            
            # Video Assembly (Durasi 26s)
            bg_path = os.path.join(tmp, "bg.mp4")
            with open(bg_path, "wb") as f: f.write(bg_video.read())
            
            clip_bg = VideoFileClip(bg_path).subclip(0, 26).resize(height=1920).crop(x_center=540, width=1080, height=1920)
            
            # Text Layers (Exact Timestamps)
            c_hook = make_text_clip(sel_hook, f_font, 90, 2, 0)
            c_stay = make_text_clip(sel_stay, f_font, 80, 3, 2, color='yellow')
            c_ques = make_text_clip(row['Q'], f_font, 75, 6, 5)
            c_timer = make_text_clip("3... 2... 1...", f_font, 120, 5, 11, bg_color=(139,0,0,200))
            c_ans = make_text_clip(row['A'], f_font, 95, 6, 16, color='lime')
            c_loop = make_text_clip("Did you get it right?\nWatch again", f_font, 70, 4, 22)

            # Audio Mixing
            audio_main = AudioFileClip(v_file)
            mixed_audio = [audio_main]
            if backsound:
                m_path = os.path.join(tmp, "m.mp3")
                with open(m_path, "wb") as f: f.write(backsound.read())
                mixed_audio.append(AudioFileClip(m_path).volumex(0.3).set_duration(26))
            if timer_sfx:
                s_path = os.path.join(tmp, "s.mp3")
                with open(s_path, "wb") as f: f.write(timer_sfx.read())
                mixed_audio.append(AudioFileClip(s_path).set_start(11).set_duration(5))

            final_video = CompositeVideoClip([clip_bg, c_hook, c_stay, c_ques, c_timer, c_ans, c_loop])
            final_video = final_video.set_audio(CompositeAudioClip(mixed_audio))
            
            out_file = os.path.join(tmp, "viral_shorts.mp4")
            final_video.write_videofile(out_file, codec="libx264", audio_codec="aac", fps=24, preset="ultrafast")
            
            with open(out_file, "rb") as f:
                download_area.download_button("📥 DOWNLOAD VIDEO", f, "viral_shorts.mp4", "video/mp4", type="primary", use_container_width=True)
            st.video(out_file)
