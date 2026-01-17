import streamlit as st
import google.generativeai as genai
import json
import time
import re

# ==========================================
# 1. KONFIGURASI HALAMAN
# ==========================================
st.set_page_config(
    page_title="Microstock Engine",
    page_icon="💎",
    layout="wide"
)

# ==========================================
# 2. SISTEM PEMBACAAN KUNCI (MODE SCANNER)
# ==========================================
def scan_for_keys():
    found_keys = []
    source = "None"

    # --- LANGKAH 1: SCAN SECRETS (Mengabaikan Struktur) ---
    try:
        # Ubah seluruh isi Secrets menjadi String tunggal
        secrets_dump = json.dumps(dict(st.secrets))
        
        # Cari pola kunci Google (AIza...) menggunakan Regex
        # Pola: AIza diikuti 35 karakter huruf/angka/garis
        matches = re.findall(r'(AIza[0-9A-Za-z\-_]{35})', secrets_dump)
        
        if matches:
            found_keys.extend(matches)
            source = "Secrets (Auto-Scan)"
    except Exception:
        pass # Lanjut cek manual jika gagal scan

    # --- LANGKAH 2: GABUNGKAN DENGAN INPUT MANUAL ---
    # Kita cek input manual dari sidebar nanti di bagian UI,
    # tapi return dulu apa yang ditemukan di secrets.
    
    # Hapus duplikat
    unique_keys = list(set(found_keys))
    return unique_keys, source

# Load keys awal dari Secrets
SECRETS_KEYS, KEY_SOURCE = scan_for_keys()
FINAL_API_KEYS = []

# ==========================================
# 3. SIDEBAR KONFIGURASI
# ==========================================
st.sidebar.header("🔌 Koneksi API")

# Input Manual (Selalu tersedia sebagai backup)
manual_input = st.sidebar.text_area("Input Manual (Jika Secrets Bermasalah)", height=100, placeholder="Paste key AIzaSy... di sini")

# LOGIKA PENGGABUNGAN KUNCI
if manual_input:
    # Jika user mengisi manual, gunakan itu
    manual_keys = [k.strip() for k in manual_input.split(',') if k.strip()]
    FINAL_API_KEYS = manual_keys
    st.sidebar.success(f"✅ Menggunakan {len(FINAL_API_KEYS)} Key Manual")
elif SECRETS_KEYS:
    # Jika manual kosong tapi Secrets ada
    FINAL_API_KEYS = SECRETS_KEYS
    st.sidebar.success(f"✅ Terhubung via Secrets")
    st.sidebar.caption(f"Deteksi: {len(FINAL_API_KEYS)} Key")
else:
    # Jika keduanya kosong
    st.sidebar.error("⚠️ Tidak ada API Key ditemukan.")
    st.sidebar.info("Mohon isi Secrets ATAU Input Manual.")

# ==========================================
# 4. AUTO-MODEL DISCOVERY
# ==========================================
@st.cache_resource
def get_best_model(_keys):
    if not _keys: return "gemini-1.5-flash"
    
    genai.configure(api_key=_keys[0])
    
    # Prioritas Model
    candidates = [
        "gemini-1.5-flash",
        "gemini-1.5-flash-latest",
        "gemini-pro",
        "models/gemini-1.5-flash"
    ]
    
    for model in candidates:
        try:
            m = genai.GenerativeModel(model)
            m.generate_content("Ping")
            return model # Model ini hidup
        except:
            continue
    
    return "gemini-1.5-flash" # Default

# Tentukan Model
ACTIVE_MODEL = "gemini-1.5-flash"
if FINAL_API_KEYS:
    try:
        ACTIVE_MODEL = get_best_model(FINAL_API_KEYS)
        st.sidebar.caption(f"Engine: {ACTIVE_MODEL}")
    except:
        pass

# ==========================================
# 5. DATA & LOGIKA GENERATOR
# ==========================================
VISUAL_MODES = {
    "1": {"name": "Isolated Object", "keywords": "white background, studio lighting, isolated on white, high quality", "ar": "--ar 1:1"},
    "2": {"name": "Copy Space", "keywords": "minimalist, wide shot, rule of thirds, negative space", "ar": "--ar 16:9"},
    "3": {"name": "Social Media", "keywords": "flatlay, aesthetic, top down view, instagram style", "ar": "--ar 4:5"},
    "4": {"name": "Line Art", "keywords": "thick outline, black and white, coloring book style, vector", "ar": "--ar 1:1"},
    "5": {"name": "Isometric", "keywords": "isometric view, 3d vector render, gradient glass texture", "ar": "--ar 16:9"}
}

def run_generation(topic, mode_key, trend, qty):
    mode = VISUAL_MODES[mode_key]
    results = []
    
    pbar = st.progress(0)
    status_text = st.empty()
    key_idx = 0
    
    for i in range(qty):
        status_text.text(f"⏳ Membuat prompt #{i+1}...")
        success = False
        attempts = 0
        
        while not success and attempts < len(FINAL_API_KEYS):
            current_key = FINAL_API_KEYS[key_idx]
            
            try:
                genai.configure(api_key=current_key)
                model = genai.GenerativeModel(ACTIVE_MODEL)
                
                sys_prompt = f"""
                Create 1 Midjourney prompt.
                Topic: {topic}. Style: {mode['name']} {trend}.
                Mandatory: {mode['keywords']} {mode['ar']} --v 6.0
                Return ONLY the raw prompt text. No JSON formatting needed.
                """
                
                response = model.generate_content(sys_prompt)
                
                # Pembersihan Output
                clean = response.text
                clean = clean.replace('```json', '').replace('```', '').replace('{', '').replace('}', '').replace('"prompt":', '').strip()
                clean = clean.strip('"') # Hapus tanda kutip sisa
                
                if len(clean) > 5:
                    results.append(clean)
                    success = True
                    # Rotasi Key
                    key_idx = (key_idx + 1) % len(FINAL_API_KEYS)
                    time.sleep(1.5) # Jeda aman
                else:
                    raise Exception("Output kosong")
                    
            except Exception as e:
                # Ganti Key jika error
                key_idx = (key_idx + 1) % len(FINAL_API_KEYS)
                attempts += 1
                time.sleep(1)
        
        if not success:
            st.error(f"❌ Gagal prompt #{i+1}. Cek kuota Key.")
            break
            
        pbar.progress((i + 1) / qty)
        
    status_text.empty()
    return results

# ==========================================
# 6. ANTARMUKA UTAMA (UI)
# ==========================================
st.title("💎 Microstock Prompt Engine")
st.markdown("---")

col1, col2 = st.columns(2)
with col1:
    topic = st.text_input("💡 Topik", placeholder="Misal: Chinese New Year Fire Horse")
    mode = st.selectbox("🎨 Mode", list(VISUAL_MODES.keys()), format_func=lambda x: VISUAL_MODES[x]['name'])
with col2:
    trend = st.text_input("📈 Trend", placeholder="Opsional")
    qty = st.number_input("🔢 Jumlah", 1, 100, 5)

if st.button("🚀 Generate Prompts", type="primary"):
    if not FINAL_API_KEYS:
        st.error("⚠️ API Key Kosong! Cek Sidebar.")
    elif not topic:
        st.error("⚠️ Topik wajib diisi.")
    else:
        res = run_generation(topic, mode, trend, qty)
        
        if res:
            # Download Section
            txt_content = "\n\n".join([f"{i+1}. {p}" for i,p in enumerate(res)])
            st.download_button("📥 Download .txt", txt_content, "prompts.txt")
            
            # Display Section (1 Blok 1 Prompt + Copy)
            st.markdown("---")
            for i, p in enumerate(res):
                st.write(f"**Prompt #{i+1}**")
                st.code(p, language="text")
