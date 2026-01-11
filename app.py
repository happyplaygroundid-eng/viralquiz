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
st.title("💀 Shorts Viral Factory (FIXED)")

# --- DATABASE HOOKS & STAY LINES ---
HOOK_DB = {
    "Ego Challenge": ["Only 1% can solve this.", "Is your IQ above 140?"],
    "Curiosity Shock": ["This feels illegal to know.", "Your brain is lying to you."],
    "Time Pressure": ["Quick! 5 seconds only.", "Decide before the timer ends!"]
}

STAY_DB = {
    "Warning": ["Don't answer too fast.", "Stop scrolling right now."],
    "Tease": ["The twist is at the end.", "You won't believe the answer."],
    "Doubt": ["You're probably wrong.", "Are you absolutely sure?"]
}

# --- SIDEBAR ---
with st.sidebar:
    st.header("🎙️ 1. Konfigurasi Suara")
    voice_choice = st.radio("Pilih Suara:", ["Male (Christopher)", "Female (Aria)"])
    voice_id = "en-US-ChristopherNeural" if "Male" in voice_choice else "en-US-AriaNeural"

    st.write("---")
    st.header("📤 Assets")
    bg_video = st.file_uploader("Upload Background Video", type=["mp4"])
    backsound = st.file_uploader("Upload Backsound", type=["mp3"])
    timer_sfx = st.file_uploader("Upload Timer SFX", type=["mp3"])
    font_file = st.file_uploader("Upload Font (.ttf)", type=["ttf"])

# --- INTERFACE ---
st.header("📝 Input Data")
quiz_csv = st.text_area("Paste CSV (Format: Pertanyaan,Jawaban)", height=100)

col_h, col_s = st.columns(2)
with col_h: hook_type = st.selectbox("🪝 Pilih Hook", list(HOOK_DB.keys()))
with col_s: stay_type = st.selectbox("🛑 Pilih Stay Line", list(STAY_DB.keys()))

async def generate_voice(text, filename, v_id):
    communicate = edge_tts.Communicate(text, v_id, rate="-5%", volume="+20%")
    await communicate.save(filename)

def make_text_clip(text, font_path, fontsize, duration, start_time, color='white'):
    W, H = 1080, 400
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    try: font = ImageFont.truetype(font_path, fontsize)
    except: font = ImageFont.load_default()
    
    wrapped = textwrap.fill(text, width=25)
    l, t, r, b = draw.multiline_textbbox((0, 0), wrapped, font=font, align='center')
    tx, ty = (W-(r-l))/2, (H-(b-t))/2
    draw.rectangle([tx-20, ty-20, tx+(r-l)+25, ty+(b-t)+25], fill=(0,0,0,180))
    draw.multiline_text((tx, ty), wrapped, font=font, fill=color, align='center')
    return ImageClip(np.array(img)).set_start(start_time).set_duration(duration).set_position(('center', 'center'))

# --- RENDER LOGIC ---
download_area = st.empty()

if st.button("🚀 GENERATE VIDEO", use_container_width=True):
    if not bg_video or not font_file or not quiz_csv:
        st.error("Bahan belum lengkap!")
    else:
        with st.spinner("Rendering... Mohon tunggu sampai selesai."):
            try:
                # 1. Path Manajemen yang Stabil
                tmp_dir = "/tmp" if os.path.exists("/tmp") else tempfile.gettempdir()
                f_font = os.path.join(tmp_dir, "f.ttf")
                with open(f_font, "wb") as f: f.write(font_file.read())
                
                data = pd.read_csv(StringIO(quiz_csv), names=["Q", "A"])
                row = data.iloc[0]
                sel_hook = random.choice(HOOK_DB[hook_type])
                sel_stay = random.choice(STAY_DB[stay_type])
                
                # 2. Audio Generation
                v_file = os.path.join(tmp_dir, "v.mp3")
                script = f"{sel_hook}. {sel_stay}. {row['Q']}. {row['A']}. Watch again."
                asyncio.run(generate_voice(script, v_file, voice_id))
                
                # 3. Video Processing
                bg_path = os.path.join(tmp_dir, "b.mp4")
                with open(bg_path, "wb") as f: f.write(bg_video.read())
                
                clip_bg = VideoFileClip(bg_path).subclip(0, 26).resize(height=1920).crop(x_center=540, width=1080, height=1920)
                
                # Layers
                c1 = make_text_clip(sel_hook, f_font, 90, 2, 0)
                c2 = make_text_clip(sel_stay, f_font, 80, 3, 2, color='yellow')
                c3 = make_text_clip(row['Q'], f_font, 75, 6, 5)
                c4 = make_text_clip("3... 2... 1...", f_font, 120, 5, 11)
                c5 = make_text_clip(row['A'], f_font, 95, 10, 16, color='lime')

                final = CompositeVideoClip([clip_bg, c1, c2, c3, c4, c5])
                
                # Audio Mix
                audios = [AudioFileClip(v_file)]
                if backsound:
                    m_path = os.path.join(tmp_dir, "m.mp3")
                    with open(m_path, "wb") as f: f.write(backsound.read())
                    audios.append(AudioFileClip(m_path).volumex(0.3).set_duration(26))
                
                final = final.set_audio(CompositeAudioClip(audios))
                
                # 4. EXPLICIT ENCODING (Anti-Error)
                out_file = os.path.join(tmp_dir, "final.mp4")
                final.write_videofile(
                    out_file, 
                    codec="libx264", 
                    audio_codec="aac", 
                    fps=24, 
                    preset="ultrafast",
                    ffmpeg_params=["-pix_fmt", "yuv420p"] # Kunci biar video bisa diputar
                )
                
                # 5. LOCK FILE TO MEMORY (Anti-0Byte)
                with open(out_file, "rb") as f:
                    final_data = f.read()
                
                if len(final_data) > 0:
                    st.success("Render Selesai!")
                    download_area.download_button(
                        label="📥 DOWNLOAD MP4", 
                        data=final_data, 
                        file_name="shorts_viral.mp4", 
                        mime="video/mp4",
                        type="primary",
                        use_container_width=True
                    )
                    st.video(final_data)
                else:
                    st.error("Gagal Render (0 Byte). Silakan coba lagi.")
                
            except Exception as e:
                st.error(f"Render Error: {e}")
