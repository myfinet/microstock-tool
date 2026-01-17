import streamlit as st
import google.generativeai as genai
import json
import time
import re

st.set_page_config(page_title="Microstock Prompt Safe", page_icon="🛡️", layout="wide")

# --- DEFINISI MODE VISUAL ---
VISUAL_MODES = {
    "1": {"name": "Isolated Object (Siap Slice)", "keywords": "white background, studio lighting, no shadow, isolated on white", "ar": "--ar 1:1"},
    "2": {"name": "Copy Space (Space Iklan)", "keywords": "minimalist, wide shot, rule of thirds, negative space on the side", "ar": "--ar 16:9"},
    "3": {"name": "Social Media Aesthetic", "keywords": "top down view, knolling, aesthetic lighting, instagram style, flatlay", "ar": "--ar 4:5"},
    "4": {"name": "Doodle & Line Art", "keywords": "thick outline, black and white, coloring book style, sticker design, vector style", "ar": "--ar 1:1"},
    "5": {"name": "Infographic & Isometric", "keywords": "isometric view, 3d vector render, gradient glass texture, tech startup vibe, --no text letters", "ar": "--ar 16:9"}
}

# --- LOAD API KEYS ---
def load_keys():
    keys = []
    # Prioritas Secrets
    if "api_keys" in st.secrets:
        val = st.secrets["api_keys"]
        if isinstance(val, list): keys = val
        elif isinstance(val, str): keys = [k.strip() for k in val.split(',') if k.strip()]
    return keys

API_KEYS = load_keys()

# --- SIDEBAR CONFIG ---
st.sidebar.header("🛡️ Konfigurasi")
if API_KEYS:
    st.sidebar.success(f"✅ {len(API_KEYS)} Key dari Secrets.")
else:
    raw = st.sidebar.text_area("Input API Key Manual (Koma)", height=100)
    if raw: API_KEYS = [k.strip() for k in raw.split(',') if k.strip()]

# Opsi Kecepatan
speed_mode = st.sidebar.radio("Kecepatan:", ["Aman (Lambat)", "Ngebut (Cepat)"], index=0)
DELAY = 5 if speed_mode == "Aman (Lambat)" else 1

# --- GENERATOR LOGIC ---
def extract_prompt(text):
    try:
        # Coba parsing JSON
        if "{" in text and "}" in text:
            # Ambil JSON pertama yang ditemukan
            json_str = re.search(r'\{.*\}', text, re.DOTALL).group(0)
            data = json.loads(json_str)
            return data.get("prompt", text)
        return text # Jika gagal, kembalikan text mentah
    except:
        return text

def run_gen(topic, mode_key, trend, qty):
    mode = VISUAL_MODES[mode_key]
    results = []
    pbar = st.progress(0)
    status = st.empty()
    
    key_idx = 0
    
    for i in range(qty):
        status.info(f"⏳ Memproses {i+1}/{qty}...")
        success = False
        attempts = 0
        
        # Retry logic: Coba sebanyak jumlah key yang ada
        while not success and attempts < len(API_KEYS):
            current_key = API_KEYS[key_idx]
            try:
                genai.configure(api_key=current_key)
                model = genai.GenerativeModel("gemini-1.5-flash")
                
                sys_prompt = f"""
                Create 1 Midjourney prompt (No intro text).
                Topic: {topic}. Style: {mode['name']} {trend}.
                Mandatory: {mode['keywords']} {mode['ar']} --v 6.0
                Return JSON: {{ "prompt": "your prompt here" }}
                """
                
                resp = model.generate_content(sys_prompt)
                final_prompt = extract_prompt(resp.text)
                final_prompt = final_prompt.replace('/imagine prompt:', '').strip()
                
                results.append(final_prompt)
                success = True
                key_idx = (key_idx + 1) % len(API_KEYS) # Putar key
                time.sleep(DELAY) # Jeda sesuai mode
                
            except Exception as e:
                # print(f"Error Key {key_idx}: {e}")
                key_idx = (key_idx + 1) % len(API_KEYS) # Ganti key
                attempts += 1
                time.sleep(1)

        if not success:
            st.error(f"❌ Gagal pada Prompt #{i+1}. Semua Key Error/Limit.")
            break
        
        pbar.progress((i+1)/qty)
        
    status.empty()
    return results

# --- UI ---
st.title("🛡️ Microstock Prompt Safe Mode")
col1, col2 = st.columns(2)
with col1:
    topic = st.text_input("💡 Topik", "Imlek Kuda Api")
    mode = st.selectbox("🎨 Mode", list(VISUAL_MODES.keys()), format_func=lambda x: VISUAL_MODES[x]['name'])
with col2:
    trend = st.text_input("Trend", "")
    qty = st.number_input("Jumlah", 1, 100, 5)

if st.button("🚀 Generate"):
    if not API_KEYS:
        st.error("Masukkan API Key dulu!")
    else:
        res = run_gen(topic, mode, trend, qty)
        if res:
            st.success("Selesai!")
            # Download
            txt = "\n\n".join([f"{i+1}. {p}" for i,p in enumerate(res)])
            st.download_button("📥 Download .txt", txt, "prompts.txt")
            # Tampilan Copy
            for i, p in enumerate(res):
                st.write(f"**Prompt #{i+1}**")
                st.code(p, language="text")
