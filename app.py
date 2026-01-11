import streamlit as st
import PIL.Image, PIL.ImageFont, PIL.ImageDraw
import os, re, random, asyncio, tempfile, textwrap
import numpy as np
import pandas as pd
from io import StringIO
from moviepy.editor import VideoFileClip, AudioFileClip, ImageClip, CompositeVideoClip, CompositeAudioClip
import edge_tts

st.set_page_config(page_title="Shorts Factory Pro", layout="wide")

if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = getattr(PIL.Image, 'LANCZOS', PIL.Image.BICUBIC)

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

# --- FUNCTIONS ---
async def generate_voice(text, filename, v_id):
    # Kecepatan dikurangi sedikit biar narasi nggak balapan sama teks
    communicate = edge_tts.Communicate(text, v_id, rate="-10%", volume="+25%")
    await communicate.save(filename)

def make_text_clip(text, font_path, fontsize, duration, start_time, color='white'):
    W, H = 1080, 1920 # Full Screen Canvas
    img = PIL.Image.new('RGBA', (W, H), (0, 0, 0, 0))
    draw = PIL.ImageDraw.Draw(img)
    try: font = PIL.ImageFont.truetype(font_path, fontsize)
    except: font = PIL.ImageFont.load_default()
    
    wrapped = textwrap.fill(text, width=20)
    l, t, r, b = draw.multiline_textbbox((0, 0), wrapped, font=font, align='center')
    
    # Render di tengah layar
    tx, ty = (W-(r-l))/2, (H-(b-t))/2
    
    # Background Box Hitam Transparan
    draw.rectangle([tx-30, ty-30, tx+(r-l)+30, ty+(b-t)+30], fill=(0,0,0,200))
    draw.multiline_text((tx, ty), wrapped, font=font, fill=color, align='center')
    
    return ImageClip(np.array(img)).set_start(start_time).set_duration(duration)

# --- UI ---
with st.sidebar:
    st.header("🎙️ Voice")
    voice_choice = st.radio("Pilih:", ["Male", "Female"])
    v_id = "en-US-ChristopherNeural" if "Male" in voice_choice else "en-US-AriaNeural"
    st.divider()
    bg_video = st.file_uploader("Upload BG", type=["mp4"])
    backsound = st.file_uploader("Upload Music", type=["mp3"])
    timer_sfx = st.file_uploader("Upload Clock SFX", type=["mp3"])
    font_file = st.file_uploader("Upload Font", type=["ttf"])

st.title("💀 Viral Shorts Pro")
quiz_csv = st.text_area("Paste CSV (Pertanyaan,Jawaban)", height=100)
download_placeholder = st.empty()

selected_row = None
if quiz_csv:
    try:
        df = pd.read_csv(StringIO(quiz_csv), names=["Pertanyaan", "Jawaban"])
        df.index = df.index + 1
        q_num = st.selectbox("🎯 Pilih Nomor:", df.index)
        selected_row = df.loc[q_num]
    except: st.error("CSV Format Error")

col1, col2 = st.columns(2)
with col1: h_type = st.selectbox("Hook:", list(HOOK_DB.keys()))
with col2: s_type = st.selectbox("Stay Line:", list(STAY_DB.keys()))

if st.button("🚀 GENERATE VIDEO", use_container_width=True):
    if not all([bg_video, font_file, selected_row is not None]):
        st.error("Bahan kurang!")
    else:
        with st.spinner("Merakit Sinkronisasi..."):
            try:
                tmp = tempfile.gettempdir()
                f_font = os.path.join(tmp, "f.ttf")
                with open(f_font, "wb") as f: f.write(font_file.read())
                
                q_txt, a_txt = selected_row['Pertanyaan'], selected_row['Jawaban']
                hook, stay = random.choice(HOOK_DB[h_type]), random.choice(STAY_DB[s_type])
                
                # 1. Generate Voice per Segmen (Biar Sinkron)
                # Kita kasih jeda antar kalimat
                v_path = os.path.join(tmp, "v.mp3")
                full_script = f"{hook}... {stay}... {q_txt}... The answer is... {a_txt}."
                asyncio.run(generate_voice(full_script, v_path, v_id))
                
                # 2. Background
                bg_p = os.path.join(tmp, "b.mp4")
                with open(bg_p, "wb") as f: f.write(bg_video.read())
                clip_bg = VideoFileClip(bg_p).subclip(0, 26).resize(height=1920).crop(x_center=540, width=1080, height=1920)
                
                # 3. Layers (Sesuai Struktur User)
                layers = [
                    clip_bg,
                    make_text_clip(hook, f_font, 100, 2, 0), # 0-2s
                    make_text_clip(stay, f_font, 90, 3, 2, color='yellow'), # 2-5s
                    make_text_clip(q_txt, f_font, 85, 6, 5), # 5-11s
                    make_text_clip("3... 2... 1...", f_font, 150, 5, 11), # 11-16s
                    make_text_clip(a_txt, f_font, 110, 6, 16, color='lime'), # 16-22s
                    make_text_clip("DID YOU GET IT?\nWatch Again", f_font, 80, 4, 22) # 22-26s
                ]
                
                # 4. Audio Mixing
                audio_v = AudioFileClip(v_path)
                audios = [audio_v.set_duration(26)]
                
                if backsound:
                    b_p = os.path.join(tmp, "m.mp3")
                    with open(b_p, "wb") as f: f.write(backsound.read())
                    audios.append(AudioFileClip(b_p).volumex(0.2).set_duration(26))
                
                if timer_sfx:
                    t_p = os.path.join(tmp, "s.mp3")
                    with open(t_p, "wb") as f: f.write(timer_sfx.read())
                    audios.append(AudioFileClip(t_p).set_start(11).set_duration(5))
                
                # 5. Assembly
                final_video = CompositeVideoClip(layers).set_audio(CompositeAudioClip(audios).set_duration(26))
                
                # 6. Export
                out_p = os.path.join(tmp, "pro.mp4")
                final_video.write_videofile(out_p, codec="libx264", audio_codec="aac", fps=24, preset="ultrafast", ffmpeg_params=["-pix_fmt", "yuv420p"])
                
                with open(out_p, "rb") as f: v_bytes = f.read()
                
                fname = re.sub(r'[^\w]', '_', q_txt)[:30] + ".mp4"
                download_placeholder.download_button(f"📥 DOWNLOAD: {fname}", v_bytes, fname, "video/mp4", type="primary", use_container_width=True)
                st.video(v_bytes)
                
            except Exception as e: st.error(f"Error: {e}")
