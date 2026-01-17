import streamlit as st
import google.generativeai as genai
import time
import sys
from google.generativeai.types import HarmCategory, HarmBlockThreshold

# --- 1. SETUP & CEK LIBRARY ---
st.set_page_config(page_title="Microstock Engine Final", page_icon="🔥", layout="wide")

# Cek Versi Library
try:
    import google.generativeai as genai
    ver = genai.__version__
    st.sidebar.markdown(f"📦 **Library Version:** `{ver}`")
except:
    st.error("❌ Library google-generativeai rusak/hilang.")
    st.stop()

# --- 2. INPUT KEY (MANUAL) ---
st.sidebar.header("🔑 API Key")
raw_input = st.sidebar.text_area("Paste Key Disini:", height=150, placeholder="AIzaSy...")

VALID_KEYS = []
if raw_input:
    # Bersihkan input
    cleaned = [k.strip().replace('"', '').replace("'", "") for k in raw_input.replace('\n', ',').split(',') if k.strip()]
    VALID_KEYS = [k for k in cleaned if k.startswith("AIza")]
    
    if VALID_KEYS:
        st.sidebar.success(f"✅ {len(VALID_KEYS)} Key Valid")
    else:
        st.sidebar.error("❌ Format Key Salah")

# --- 3. KONFIGURASI SAFETY (PENTING!) ---
# Ini mematikan sensor agar prompt tidak diblokir karena dianggap 'unsafe'
SAFETY_SETTINGS = {
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
}

# --- 4. GENERATOR CORE ---
VISUAL_MODES = {
    "1": {"name": "Isolated Object", "keywords": "white background, studio lighting, isolated on white", "ar": "--ar 1:1"},
    "2": {"name": "Copy Space", "keywords": "minimalist, negative space, rule of thirds", "ar": "--ar 16:9"},
    "3": {"name": "Social Media", "keywords": "flatlay, aesthetic, top down view", "ar": "--ar 4:5"},
    "4": {"name": "Line Art", "keywords": "thick outline, black and white, vector style", "ar": "--ar 1:1"},
    "5": {"name": "Isometric", "keywords": "isometric view, 3d vector render", "ar": "--ar 16:9"}
}

def run_gen(topic, mode_key, trend, qty):
    mode = VISUAL_MODES[mode_key]
    results = []
    
    log = st.expander("📜 Log Detil (Debug)", expanded=True)
    pbar = st.progress(0)
    key_idx = 0
    
    # DAFTAR MODEL (Flash -> Pro -> 1.0)
    # Kita paksa coba semua jenis model sampai ada yang nyangkut
    MODELS = ["gemini-1.5-flash", "gemini-1.5-flash-latest", "gemini-pro", "gemini-1.0-pro"]

    for i in range(qty):
        success = False
        attempts = 0
        
        while not success and attempts < len(VALID_KEYS):
            current_key = VALID_KEYS[key_idx]
            masked = f"...{current_key[-4:]}"
            
            genai.configure(api_key=current_key)
            
            for model_name in MODELS:
                try:
                    model = genai.GenerativeModel(model_name)
                    
                    # Prompt sederhana teks biasa
                    prompt = f"Write 1 Midjourney prompt for '{topic}', style '{mode['name']}'. Mandatory: {mode['keywords']} {mode['ar']}. Output raw text only."
                    
                    # KIRIM REQUEST DENGAN SAFETY SETTINGS OFF
                    response = model.generate_content(
                        prompt, 
                        safety_settings=SAFETY_SETTINGS
                    )
                    
                    if response.text:
                        clean_text = response.text.replace('`','').replace('"prompt":','').strip()
                        results.append(clean_text)
                        log.success(f"✅ Berhasil (Key: {masked} | Model: {model_name})")
                        success = True
                        break # Break loop model
                        
                except Exception as e:
                    err = str(e)
                    # Cek error spesifik
                    if "429" in err:
                        # Limit habis, ganti key
                        break 
                    elif "404" in err or "not found" in err:
                        # Model tidak ketemu, lanjut loop model berikutnya (jangan ganti key dulu)
                        continue 
                    elif "400" in err:
                         # Key Invalid, atau IP blocked
                        log.error(f"❌ Key {masked} Error 400: {err}")
                        break
                    else:
                        # Error lain
                        continue
            
            if success:
                key_idx = (key_idx + 1) % len(VALID_KEYS)
                time.sleep(1)
                break
            else:
                # Ganti Key
                key_idx = (key_idx + 1) % len(VALID_KEYS)
                attempts += 1
                time.sleep(1)
        
        if not success:
            st.error(f"❌ Gagal Prompt #{i+1}. Cek Log di atas untuk melihat error aslinya.")
            break
            
        pbar.progress((i+1)/qty)
        
    return results

# --- UI ---
st.title("🔥 Microstock Engine (Uncensored)")
col1, col2 = st.columns(2)
with col1:
    topic = st.text_input("Topik", "Chinese New Year")
    mode = st.selectbox("Mode", list(VISUAL_MODES.keys()))
with col2:
    trend = st.text_input("Trend", "")
    qty = st.number_input("Jumlah", 1, 100, 5)

if st.button("🚀 Generate Now", type="primary"):
    if not VALID_KEYS:
        st.error("Paste Key di Sidebar dulu!")
    else:
        res = run_gen(topic, mode, trend, qty)
        if res:
            st.success("Selesai!")
            for idx, p in enumerate(res):
                st.write(f"**#{idx+1}**")
                st.code(p, language="text")
