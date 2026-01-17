import streamlit as st
import google.generativeai as genai
import time

st.set_page_config(page_title="Microstock Engine Auto", page_icon="🤖", layout="wide")

st.title("🤖 Microstock Engine (Auto-Model)")
st.info("Script ini akan mencari model yang tersedia secara otomatis.")

# --- 1. SETUP API KEY ---
st.sidebar.header("🔑 Setup Key")
raw_keys = st.sidebar.text_area("Paste 10 Key Anda:", height=150)

CLEAN_KEYS = []
if raw_keys:
    # Bersihkan input
    candidates = raw_keys.replace('\n', ',').split(',')
    for c in candidates:
        k = c.strip().replace('"', '').replace("'", "")
        if k.startswith("AIza") and len(k) > 30:
            CLEAN_KEYS.append(k)

    if CLEAN_KEYS:
        st.sidebar.success(f"✅ {len(CLEAN_KEYS)} Key Valid")
    else:
        st.sidebar.error("❌ Format Key Salah")

# --- 2. FUNGSI PENCARI MODEL (OBAT 404) ---
def get_available_model(api_key):
    """Bertanya ke Google: Model apa yang boleh saya pakai?"""
    try:
        # PENTING: Pakai transport='rest' agar tembus firewall
        genai.configure(api_key=api_key, transport='rest')
        
        # Ambil daftar model
        for m in genai.list_models():
            # Cari model yang bisa generate text (generateContent)
            if 'generateContent' in m.supported_generation_methods:
                # Prioritaskan Flash jika ada, tapi terima apa saja
                if 'flash' in m.name: return m.name
                if 'gemini-1.5' in m.name: return m.name
        
        # Jika loop selesai tapi belum return, ambil model pertama yg generateContent
        for m in genai.list_models():
             if 'generateContent' in m.supported_generation_methods:
                 return m.name
                 
    except Exception as e:
        return None
    return "models/gemini-pro" # Fallback terakhir

# --- 3. GENERATOR LOGIC ---
VISUAL_MODES = {
    "1": {"name": "Isolated Object", "keywords": "white background, studio lighting", "ar": "--ar 1:1"},
    "2": {"name": "Copy Space", "keywords": "minimalist, negative space", "ar": "--ar 16:9"},
    "3": {"name": "Social Media", "keywords": "flatlay, aesthetic", "ar": "--ar 4:5"},
    "4": {"name": "Line Art", "keywords": "thick outline, black and white", "ar": "--ar 1:1"},
    "5": {"name": "Isometric", "keywords": "isometric view, 3d vector", "ar": "--ar 16:9"}
}

def run_gen(topic, mode_key, trend, qty):
    mode = VISUAL_MODES[mode_key]
    results = []
    log = st.expander("Logs", expanded=True)
    pbar = st.progress(0)
    key_idx
