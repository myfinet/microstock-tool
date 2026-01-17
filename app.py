import streamlit as st
import google.generativeai as genai
import json
import time
import re

st.set_page_config(page_title="Microstock Engine (Final)", page_icon="💎", layout="wide")

# --- 1. LOGIKA PEMBACAAN SECRETS AGRESIF ---
# Fungsi ini tidak peduli nama variabelnya apa. 
# Dia akan mencari teks berawalan 'AIza' di mana saja.
def load_api_keys_aggressively():
    keys = []
    
    # 1. Coba baca secrets
    try:
        # Loop semua item yang ada di secrets
        for key, value in st.secrets.items():
            # Jika isinya String dan berawalan AIza
            if isinstance(value, str):
                if "AIza" in value:
                    # Pecah jika ada koma
                    parts = [k.strip() for k in value.split(',') if k.strip()]
                    keys.extend(parts)
            
            # Jika isinya List (Daftar)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, str) and "AIza" in item:
                        keys.append(item.strip())
                        
    except Exception:
        pass # Lanjut ke manual jika gagal
        
    # Hapus duplikat dan kunci kosong
    unique_keys = list(set([k for k in keys if len(k) > 30]))
    return unique_keys

# Load Keys
API_KEYS = load_api_keys_aggressively()

# --- 2. SIDEBAR STATUS (JUJUR) ---
st.sidebar.header("🔌 Status Koneksi")

if API_KEYS:
    st.sidebar.success(f"✅ Ditemukan {len(API_KEYS)} API Key!")
    # Tampilkan sedikit buntut key untuk verifikasi
    st.sidebar.caption(f"Menggunakan: ...{API_KEYS[0][-6:]}")
else:
    st.sidebar.error("❌ SECRETS TIDAK TERDETEKSI")
    st.sidebar.info("Gunakan Input Manual di bawah ini:")
    # INPUT MANUAL YANG SELALU MUNCUL JIKA SECRETS GAGAL
    manual_input = st.sidebar.text_area("Paste API Key Di Sini (Wajib jika Secrets Error)", height=150, placeholder="AIzaSy...")
    if manual_input:
        API_KEYS = [k.strip() for k in manual_input.split(',') if k.strip()]
        if API_KEYS: st.sidebar.success("✅ Key Manual Siap!")

# --- 3. AUTO-DETECT MODEL (Anti-404) ---
# Menggunakan cache agar tidak melambat setiap kali klik
@st.cache_resource
def get_working_model(_keys):
    if not _keys: return None
    
    # Cek Key pertama saja untuk menentukan model
    test_key = _keys[0]
    genai.configure(api_key=test_key)
    
    models_to_test = [
        "gemini-1.5-flash", 
        "gemini-1.5-flash-latest", 
        "gemini-pro", 
        "models/gemini-1.5-flash"
    ]
    
    for m in models_to_test:
        try:
            model = genai.GenerativeModel(m)
            # Test ping
            model.generate_content("Hi")
            return m # Jika berhasil, kembalikan nama modelnya
        except:
            continue
            
    return "gemini-1.5-flash" # Default nekat

# Tentukan model sekali saja
if API_KEYS:
    ACTIVE_MODEL = get_working_model(API_KEYS)
    st.sidebar.caption(f"Engine: {ACTIVE_MODEL}")
else:
    ACTIVE_MODEL = "gemini-1.5-flash"

# --- 4. DATA MODE VISUAL ---
VISUAL_MODES = {
    "1": {"name": "Isolated Object", "keywords": "white background, studio lighting, isolated on white", "ar": "--ar 1:1"},
    "2": {"name": "Copy Space", "keywords": "minimalist, negative space, rule of thirds", "ar": "--ar 16:9"},
    "3": {"name": "Social Media", "keywords": "flatlay, aesthetic, top down view", "ar": "--ar 4:5"},
    "4": {"name": "Line Art", "keywords": "black and white, thick outline, coloring book", "ar": "--ar 1:1"},
    "5": {"name": "Isometric", "keywords": "3d vector, isometric view, gradient glass", "ar": "--ar 16:9"}
}

# --- 5. GENERATOR CORE ---
def generate_prompts(topic, mode_key, trend, qty):
    mode = VISUAL_MODES[mode_key]
    results = []
    
    pbar = st.progress(0)
    status = st.empty()
    key_idx = 0
    
    for i in range(qty):
        status.text(f"⏳ Membuat prompt #{i+1}...")
        success = False
        attempts = 0
        
        while not success and attempts < len(API_KEYS):
            # Rotasi Key
            current_key = API_KEYS[key_idx]
            
            try:
                genai.configure(api_key=current_key)
                model = genai.GenerativeModel(ACTIVE_MODEL)
                
                prompt = f"""
                Create 1 Midjourney prompt description ONLY.
                Topic: {topic}. Style: {mode['name']} {trend}.
                Mandatory: {mode['keywords']} {mode['ar']} --v 6.0
                Return raw text only. No introduction.
                """
                
                resp = model.generate_content(prompt)
                
                # Bersihkan teks sampah
                clean = resp.text
                clean = clean.replace('```json','').replace('```','').replace('{','').replace('}','').replace('"prompt":','').strip()
                clean = clean.strip('"')
                
                if len(clean) > 10: # Pastikan bukan text kosong
                    results.append(clean)
                    success = True
                    # Geser key
                    key_idx = (key_idx + 1) % len(API_KEYS)
                    time.sleep(1.5)
                else:
                    raise Exception("Output kosong")

            except Exception as e:
                # print(e) # Debug
                key_idx = (key_idx + 1) % len(API_KEYS)
                attempts += 1
                time.sleep(1)
        
        if not success:
            st.error(f"Gagal prompt #{i+1}. Cek kuota Key.")
            break
            
        pbar.progress((i+1)/qty)
    
    status.empty()
    return results

# --- 6. UI UTAMA ---
st.title("💎 Microstock Prompt Engine")

col1, col2 = st.columns(2)
with col1:
    topic = st.text_input("💡 Topik", "Chinese New Year Fire Horse")
    mode = st.selectbox("🎨 Mode", list(VISUAL_MODES.keys()), format_func=lambda x: VISUAL_MODES[x]['name'])
with col2:
    trend = st.text_input("📈 Trend", "")
    qty = st.number_input("🔢 Jumlah", 1, 100, 5)

if st.button("🚀 Generate", type="primary"):
    if not API_KEYS:
        st.error("API KEY KOSONG! Masukkan manual di Sidebar.")
    else:
        res = generate_prompts(topic, mode, trend, qty)
        if res:
            # Download
            txt = "\n\n".join([f"{i+1}. {p}" for i,p in enumerate(res)])
            st.download_button("📥 Download .txt", txt, "prompts.txt")
            
            # Tampilan Copy
            st.markdown("---")
            for i, p in enumerate(res):
                st.write(f"**Prompt #{i+1}**")
                st.code(p, language="text")
