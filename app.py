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

# FIX COMPATIBILITY UNTUK PYTHON 3.13 + PILLOW
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = getattr(PIL.Image, 'LANCZOS', PIL.Image.BICUBIC)

# FIX IMPORT MOVIEPY (Cara paling aman buat semua versi)
try:
    from moviepy.editor import VideoFileClip, AudioFileClip, ImageClip, CompositeVideoClip, CompositeAudioClip, afx
except ImportError:
    try:
        from moviepy.video.io.VideoFileClip import VideoFileClip
        from moviepy.audio.io.AudioFileClip import AudioFileClip
        from moviepy.video.VideoClip import ImageClip
        from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip
        from moviepy.audio.AudioClip import CompositeAudioClip
        from moviepy.audio.fx.all import audio_loop as aloop
        # Helper untuk akses afx di versi baru
        class afx_dummy:
            @staticmethod
            def audio_loop(clip, duration): return aloop(clip, duration=duration)
        afx = afx_dummy()
    except Exception as e:
        st.error(f"Gagal memuat library MoviePy: {e}")

import edge_tts

st.set_page_config(page_title="Viral Shorts Factory", layout="wide")
st.title("💀 Viral Shorts Factory (Stable Build)")

# --- DATABASE HOOKS & STAY LINES (300 ALTERNATIVES LOGIC) ---
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

# --- SIDEBAR ASSETS ---
with st.sidebar:
    st.header("🎙️ 1. Suara (US Native)")
    voice_choice = st.radio("Pilih Suara:", ["Male (Christopher)", "Female (Aria)"])
    voice_id = "en-US-ChristopherNeural" if "Male" in voice_choice else "en-US-AriaNeural"

    st.write("---")
    st.header("📤 2, 3, 4. Assets")
    bg_video = st.file_uploader("Upload Background Video", type=["mp4"])
    backsound = st.file_uploader("Upload Backsound", type=["mp3"])
    timer_sfx = st.file_uploader("Upload Timer SFX", type=["mp3"])
    font_file = st.file_uploader("Upload Font (.ttf)", type=["ttf"])

# --- INPUT DATA ---
st.header("📝 0. Data Kuis")
quiz_csv = st.text_area("Paste CSV (Format: Pertanyaan,Jawaban)", height=100, placeholder="Who is...?,The King!")

col_h, col_s = st.columns(2)
with col_h: hook_type = st.selectbox("🪝 5. Pilih Jenis Hook", list(HOOK_DB.keys()))
with col_s: stay_type = st.selectbox("🛑 6. Pilih Jenis Stay Line", list(STAY_DB.keys()))

# --- CORE FUNCTIONS ---
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

# --- RENDER EXECUTION ---
download_area = st.empty()

if st.button("🚀 GENERATE VIDEO", use_container_width=True):
    if not bg_video or not font_file or not quiz_csv:
        st.error("Lengkapi Bahan Dulu!")
    else:
        with st.spinner("Rendering... (Fixing 0B & Codec Issues)"):
            try:
                tmp_dir = "/tmp" if os.path.exists("/tmp") else tempfile.gettempdir()
                
                # Simpan Font
                f_font = os.path.join(tmp_dir, "f.ttf")
                with open(f_font, "wb") as f: f.write(font_file.read())
                
                # Pilih Data
                data = pd.read_csv(StringIO(quiz_csv), names=["Q", "A"])
                row = data.iloc[0]
                sel_hook = random.choice(HOOK_DB[hook_type])
                sel_stay = random.choice(STAY_DB[stay_type])
                
                # Generate Audio
                v_file = os.path.join(tmp_dir, "v.mp3")
                script = f"{sel_hook}. {sel_stay}. {row['Q']}. {row['A']}. Watch again."
                asyncio.run(generate_voice(script, v_file, voice_id))
                
                # Video Processing
                bg_path = os.path.join(tmp_dir, "b.mp4")
                with open(bg_path, "wb") as f: f.write(bg_video.read())
                
                clip_bg = VideoFileClip(bg_path).subclip(0, 26).resize(height=1920).crop(x_center=540, width=1080, height=1920)
                
                # Layers Teks (Sesuai Struktur)
                c1 = make_text_clip(sel_hook, f_font, 95, 2, 0) # 0-2s
                c2 = make_text_clip(sel_stay, f_font, 85, 3, 2, color='yellow') # 2-5s
                c3 = make_text_clip(row['Q'], f_font, 80, 6, 5) # 5-11s
                c4 = make_text_clip("3... 2... 1...", f_font, 130, 5, 11) # 11-16s
                c5 = make_text_clip(row['A'], f_font, 100, 6, 16, color='lime') # 16-22s
                c6 = make_text_clip("DID YOU GET IT?\nWatch Again", f_font, 75, 4, 22) # 22-26s

                final = CompositeVideoClip([clip_bg, c1, c2, c3, c4, c5, c6])
                
                # Mix Audio
                audios = [AudioFileClip(v_file)]
                if backsound:
                    m_p = os.path.join(tmp_dir, "m.mp3")
                    with open(m_p, "wb") as f: f.write(backsound.read())
                    audios.append(AudioFileClip(m_p).volumex(0.3).set_duration(26))
                
                final = final.set_audio(CompositeAudioClip(audios))
                
                # RENDER DENGAN FIX ENCODING
                out_file = os.path.join(tmp_dir, "out.mp4")
                final.write_videofile(out_file, codec="libx264", audio_codec="aac", fps=24, 
                                     preset="ultrafast", ffmpeg_params=["-pix_fmt", "yuv420p"])
                
                # LOCK TO MEMORY (Anti-0B)
                with open(out_file, "rb") as f:
                    v_bytes = f.read()
                
                st.success("✅ Selesai!")
                download_area.download_button("📥 DOWNLOAD VIDEO", v_bytes, "viral_shorts.mp4", "video/mp4", type="primary", use_container_width=True)
                st.video(v_bytes)
                
            except Exception as e:
                st.error(f"Error: {e}")
