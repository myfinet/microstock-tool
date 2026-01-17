import streamlit as st
import google.generativeai as genai
import json
import time
import re

st.set_page_config(page_title="Microstock Engine (Auto-Model)", page_icon="🤖", layout="wide")

# --- DEFINISI DATA ---
VISUAL_MODES = {
    "1": {"name": "Isolated Object", "keywords": "white background, studio lighting, no shadow, isolated on white", "ar": "--ar 1:1"},
    "2": {"name": "Copy Space", "keywords": "minimalist, wide shot, rule of thirds, negative space", "ar": "--ar 16:9"},
    "3": {"name": "Social Media", "keywords": "top down view, flatlay, aesthetic lighting", "ar": "--ar 4:5"},
    "4": {"name": "Line Art", "keywords": "thick outline, black and white, coloring book style", "ar": "--ar 1:1"},
    "5": {"name": "Isometric", "keywords": "isometric view, 3d vector render, gradient glass", "ar": "--ar 16:9"}
}

# --- LOAD API KEYS ---
def load_keys():
    keys = []
    if "api_keys" in st.secrets:
        val = st.secrets["api_keys"]
        if isinstance(val, list): keys = val
        elif isinstance(val, str): keys = [k.strip() for k in val.split(',') if k.strip()]
    return keys

API_KEYS = load_keys()

# --- FUNGSI PENCARI MODEL OTOMATIS (AUTO-DISCOVERY) ---
# Ini adalah obat untuk Error 404. Dia mencari model yang BENAR-BENAR ADA.
@st.cache_resource
def find_valid_model(_api_key):
    genai.configure(api_key=_api_key)
    try:
        # Minta daftar model ke Google
        available_models = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                available_models.append(m.name)
        
        # Prioritas pemilihan model (Cari Flash dulu, kalau gak ada cari Pro)
        # Kita cari string yang mengandung kata kunci, bukan exact match
        for m in available_models:
            if "flash" in m and "1.5" in m: return m # Prioritas 1: Gemini 1.5 Flash
        
        for m in available_models:
            if "flash" in m: return m # Prioritas 2: Flash versi lain
            
        for m in available_models:
            if "pro" in m and "1.5" in m: return m # Prioritas 3: Gemini 1.5 Pro
            
        for m in available_models:
            if "pro" in m: return m # Prioritas 4: Gemini 1.0 Pro (Cadangan Terakhir)
            
        return "models/gemini-pro" # Fallback manual jika list kosong
        
    except Exception as e:
        return None

# Sidebar Status
st.sidebar.header("⚙️ Konfigurasi")
active_model_name = "Belum Terdeteksi"

if API_KEYS:
    # Cek model menggunakan Key pertama
    found_model = find_valid_model(API_KEYS[0])
    if found_model:
        active_model_name = found_model
        st.sidebar.success(f"✅ Key Aktif\n🧠 Model: {found_model}")
    else:
        st.sidebar.error("❌ Key Error / Tidak bisa list model.")
else:
    st.sidebar.warning("⚠️ Secrets Kosong.")
    manual = st.sidebar.text_area("Input API Key Manual", height=100)
    if manual: API_KEYS = [k.strip() for k in manual.split(',')]


# --- GENERATOR LOGIC ---
def run_generation(topic, mode_key, trend, qty):
    mode = VISUAL_MODES[mode_key]
    results = []
    
    pbar = st.progress(0)
    status_text = st.empty()
    key_idx = 0
    
    for i in range(qty):
        status_text.text(f"⏳ Membuat prompt {i+1}/{qty}...")
        success = False
        attempts = 0
        
        while not success and attempts < len(API_KEYS):
            current_key = API_KEYS[key_idx]
            
            try:
                genai.configure(api_key=current_key)
                
                # Gunakan nama model yang tadi sudah ditemukan secara otomatis
                model_to_use = active_model_name if active_model_name else "models/gemini-pro"
                model = genai.GenerativeModel(model_to_use)
                
                sys_prompt = f"""
                Create 1 Midjourney prompt description ONLY.
                Topic: {topic}. Style: {mode['name']} {trend}.
                Mandatory: {mode['keywords']} {mode['ar']} --v 6.0
                Do NOT include introduction text.
                """
                
                response = model.generate_content(sys_prompt)
                
                # Pembersih Text
                clean = response.text.replace('```json', '').replace('```', '').replace('{', '').replace('}', '').replace('"prompt":', '').replace('/imagine prompt:', '').strip()
                clean = clean.strip('"')
                
                results.append(clean)
                success = True
                
                # Rotasi Key
                key_idx = (key_idx + 1) % len(API_KEYS)
                time.sleep(1.5) # Jeda aman
                
            except Exception as e:
                # print(f"Error: {e}") 
                # Jika error, ganti key
                key_idx = (key_idx + 1) % len(API_KEYS)
                attempts += 1
                time.sleep(1)
        
        if not success:
            st.error(f"❌ Gagal pada prompt #{i+1}. Semua Key limit/error.")
            break
            
        pbar.progress((i + 1) / qty)
        
    status_text.empty()
    return results

# --- UI UTAMA ---
st.title("🤖 Microstock Engine (Auto-Model)")
st.caption(f"Menggunakan Model Engine: {active_model_name}")

col1, col2 = st.columns(2)
with col1:
    topic = st.text_input("💡 Topik", "Chinese New Year Fire Horse")
    mode = st.selectbox("🎨 Mode", list(VISUAL_MODES.keys()), format_func=lambda x: VISUAL_MODES[x]['name'])
with col2:
    trend = st.text_input("📈 Trend", "")
    qty = st.number_input("🔢 Jumlah", 1, 100, 5)

if st.button("🚀 Generate Prompts", type="primary"):
    if not API_KEYS:
        st.error("Masukkan API Key!")
    elif "Belum" in active_model_name:
        st.error("Gagal mendeteksi model. Cek API Key Anda.")
    else:
        res = run_generation(topic, mode, trend, qty)
        
        if res:
            st.success("Selesai!")
            # Download
            txt = "\n\n".join([f"{i+1}. {p}" for i,p in enumerate(res)])
            st.download_button("📥 Download .txt", txt, "prompts.txt")
            
            st.markdown("---")
            for i, p in enumerate(res):
                st.write(f"**Prompt #{i+1}**")
                st.code(p, language="text")
