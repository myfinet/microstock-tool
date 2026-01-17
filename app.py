import streamlit as st
import google.generativeai as genai
import json
import time
import re

st.set_page_config(page_title="Microstock Engine (Debug)", page_icon="🛠️", layout="wide")

# --- DEFINISI MODE VISUAL ---
VISUAL_MODES = {
    "1": {"name": "Isolated Object", "keywords": "white background, isolated on white", "ar": "--ar 1:1"},
    "2": {"name": "Copy Space", "keywords": "minimalist, negative space", "ar": "--ar 16:9"},
    "3": {"name": "Social Media", "keywords": "flatlay, aesthetic", "ar": "--ar 4:5"},
    "4": {"name": "Line Art", "keywords": "black and white, outline", "ar": "--ar 1:1"},
    "5": {"name": "Isometric", "keywords": "3d vector, isometric", "ar": "--ar 16:9"}
}

# --- LOAD KEYS ---
def load_keys():
    keys = []
    if "api_keys" in st.secrets:
        val = st.secrets["api_keys"]
        if isinstance(val, list): keys = val
        elif isinstance(val, str): keys = [k.strip() for k in val.split(',') if k.strip()]
    return keys

API_KEYS = load_keys()

st.sidebar.header("🛠️ Status Debug")
if API_KEYS:
    st.sidebar.success(f"✅ {len(API_KEYS)} Key Terbaca")
    # Tampilkan 4 huruf awal key pertama untuk memastikan benar
    st.sidebar.code(f"Key 1: {API_KEYS[0][:4]}... (Cek apakah benar)")
else:
    st.sidebar.error("❌ TIDAK ADA KEY TERBACA DARI SECRETS!")
    manual = st.sidebar.text_area("Input Manual (Darurat)", height=100)
    if manual: API_KEYS = [k.strip() for k in manual.split(',')]

# --- GENERATOR LOGIC ---
def run_debug(topic, mode_key, trend, qty):
    mode = VISUAL_MODES[mode_key]
    results = []
    log_box = st.expander("📜 Log Proses (Buka jika Error)", expanded=True)
    
    key_idx = 0
    
    for i in range(qty):
        success = False
        attempts = 0
        
        while not success and attempts < len(API_KEYS):
            key = API_KEYS[key_idx]
            masked_key = key[:5] + "..."
            
            try:
                genai.configure(api_key=key)
                # Kita gunakan model 'gemini-1.5-flash' yang paling standar
                model = genai.GenerativeModel("gemini-1.5-flash")
                
                log_box.write(f"🔄 Prompt #{i+1}: Mencoba Key {masked_key}...")
                
                # Prompt yang lebih fleksibel (tidak memaksa JSON keras)
                resp = model.generate_content(f"""
                Create 1 Midjourney prompt for "{topic}", style "{mode['name']}".
                Keywords: {mode['keywords']} {mode['ar']} --v 6.0
                Do NOT include introduction text. Just the prompt.
                """)
                
                # Coba ambil teksnya
                if resp.text:
                    # Bersihkan hasil
                    clean = resp.text.replace('```json', '').replace('```', '').replace('{', '').replace('}', '').replace('"prompt":', '').replace('/imagine prompt:', '').strip()
                    # Bersihkan tanda kutip di awal/akhir jika ada
                    clean = clean.strip('"')
                    
                    results.append(clean)
                    log_box.success(f"✅ Sukses Key {masked_key}")
                    success = True
                    key_idx = (key_idx + 1) % len(API_KEYS)
                else:
                    log_box.warning(f"⚠️ Key {masked_key} merespon tapi kosong (Blocked?).")
                    attempts += 1
                    
            except Exception as e:
                # INI BAGIAN PENTING: TAMPILKAN ERROR ASLINYA
                err_msg = str(e)
                log_box.error(f"❌ ERROR Key {masked_key}: {err_msg}")
                
                # Pindah key
                key_idx = (key_idx + 1) % len(API_KEYS)
                attempts += 1
                time.sleep(1)
        
        if not success:
            st.error(f"Gagal total pada prompt #{i+1}. Lihat log di atas.")
            break
            
    return results

# --- UI ---
st.title("🛠️ Microstock (Mode Diagnostik)")
topic = st.text_input("Topik", "Cat") # Topik pendek untuk tes
mode = st.selectbox("Mode", list(VISUAL_MODES.keys()))
qty = st.number_input("Jumlah", 1, 10, 1)

if st.button("🚀 Test Run"):
    if not API_KEYS:
        st.error("Masukkan Key dulu!")
    else:
        res = run_debug(topic, mode, "", qty)
        if res:
            st.success("Berhasil!")
            for p in res: st.code(p, language="text")
