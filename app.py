import streamlit as st
import google.generativeai as genai
import time
import random

st.set_page_config(page_title="Microstock Engine (Final Fix)", page_icon="🔧", layout="wide")

# ==========================================
# 1. INPUT KEY (DIRECT & MANUAL)
# ==========================================
st.sidebar.header("🔑 API Key Setup")
st.sidebar.info("Masukkan 10 Key Anda di bawah ini (Copy-Paste semua sekaligus).")

# Kita prioritaskan Input Manual agar TIDAK ADA keraguan soal "Secrets Kosong"
input_keys = st.sidebar.text_area("Paste API Keys (Pisahkan koma)", height=200, placeholder="AIzaSy...,\nAIzaSy...,\nAIzaSy...")

API_KEYS = []
if input_keys:
    # Membersihkan input dari spasi/enter yang tidak perlu
    API_KEYS = [k.strip() for k in input_keys.replace('\n', ',').split(',') if k.strip()]
    st.sidebar.success(f"✅ {len(API_KEYS)} Key Siap Digunakan!")
elif "api_keys" in st.secrets:
    # Fallback ke secrets jika manual kosong
    val = st.secrets["api_keys"]
    if isinstance(val, str): API_KEYS = [k.strip() for k in val.split(',') if k.strip()]
    elif isinstance(val, list): API_KEYS = val
    if API_KEYS: st.sidebar.warning(f"ℹ️ Menggunakan {len(API_KEYS)} Key dari Secrets (Input manual kosong).")

# ==========================================
# 2. LOGIKA GENERATOR (DENGAN ERROR ASLI)
# ==========================================
VISUAL_MODES = {
    "1": {"name": "Isolated Object", "keywords": "white background, studio lighting, isolated on white", "ar": "--ar 1:1"},
    "2": {"name": "Copy Space", "keywords": "minimalist, negative space, rule of thirds", "ar": "--ar 16:9"},
    "3": {"name": "Social Media", "keywords": "flatlay, aesthetic, top down view", "ar": "--ar 4:5"},
    "4": {"name": "Line Art", "keywords": "thick outline, black and white, vector style", "ar": "--ar 1:1"},
    "5": {"name": "Isometric", "keywords": "isometric view, 3d vector render", "ar": "--ar 16:9"}
}

# Daftar model yang akan dicoba satu per satu jika gagal
MODELS_TO_TRY = [
    "gemini-1.5-flash",
    "gemini-1.5-flash-latest",
    "gemini-pro",
    "gemini-1.0-pro"
]

def run_generator(topic, mode_key, trend, qty):
    mode = VISUAL_MODES[mode_key]
    results = []
    
    # Area Log untuk melihat apa yang terjadi
    log_area = st.expander("📜 Lihat Log Proses (Klik di sini jika error)", expanded=True)
    
    progress = st.progress(0)
    key_idx = 0
    
    for i in range(qty):
        success = False
        attempts = 0
        
        # Loop Key (Rotasi)
        while not success and attempts < len(API_KEYS):
            current_key = API_KEYS[key_idx]
            masked_key = f"{current_key[:5]}...{current_key[-3:]}"
            
            genai.configure(api_key=current_key)
            
            # Loop Model (Jika model A gagal, coba model B di key yang sama)
            for model_name in MODELS_TO_TRY:
                try:
                    model = genai.GenerativeModel(model_name)
                    
                    # Prompt Sederhana (Raw Text)
                    prompt = f"""
                    Create 1 Midjourney prompt for "{topic}", style "{mode['name']} {trend}".
                    Mandatory: {mode['keywords']} {mode['ar']} --v 6.0
                    Output only the prompt text.
                    """
                    
                    response = model.generate_content(prompt)
                    
                    # Jika berhasil
                    if response.text:
                        clean_text = response.text.replace('```json','').replace('```','').replace('"prompt":','').strip().strip('"')
                        results.append(clean_text)
                        
                        log_area.success(f"✅ Prompt #{i+1} Berhasil (Key: {masked_key} | Model: {model_name})")
                        success = True
                        break # Keluar dari loop model
                        
                except Exception as e:
                    err_msg = str(e)
                    # HANYA TAMPILKAN ERROR JIKA BUKAN 429 (LIMIT) ATAU 404 (NOT FOUND)
                    # AGAR LOG TIDAK PENUH
                    if "429" in err_msg:
                        log_area.warning(f"⚠️ Key {masked_key} Limit Habis. Ganti Key...")
                        break # Ganti key, jangan coba model lain di key ini
                    elif "404" in err_msg or "not found" in err_msg:
                        # Log kecil saja, lanjut coba model berikutnya
                        continue 
                    else:
                        # Tampilkan Error Aneh (Ini yang kita cari)
                        log_area.error(f"❌ ERROR ASLI (Key {masked_key}): {err_msg}")
                        break

            if success:
                # Rotasi key untuk prompt berikutnya
                key_idx = (key_idx + 1) % len(API_KEYS)
                time.sleep(1) # Jeda aman
                break # Lanjut ke prompt i+1
            else:
                # Ganti Key
                key_idx = (key_idx + 1) % len(API_KEYS)
                attempts += 1
        
        if not success:
            st.error(f"❌ Gagal total pada prompt #{i+1}. Semua {len(API_KEYS)} Key gagal. Cek Log di atas.")
            break
            
        progress.progress((i + 1) / qty)
        
    return results

# ==========================================
# 3. UI UTAMA
# ==========================================
st.title("🔧 Microstock Engine (Direct Mode)")
st.markdown("---")

col1, col2 = st.columns(2)
with col1:
    topic = st.text_input("💡 Topik", "Chinese New Year")
    mode = st.selectbox("🎨 Mode", list(VISUAL_MODES.keys()), format_func=lambda x: VISUAL_MODES[x]['name'])
with col2:
    trend = st.text_input("📈 Trend", "")
    qty = st.number_input("🔢 Jumlah", 1, 100, 5)

if st.button("🚀 Generate (Debug Run)", type="primary"):
    if not API_KEYS:
        st.error("⚠️ TOLONG COPY-PASTE KEY ANDA DI SIDEBAR DULU!")
    else:
        res = run_generator(topic, mode, trend, qty)
        if res:
            st.success("Selesai!")
            # Tampilan Copy
            for idx, p in enumerate(res):
                st.write(f"**#{idx+1}**")
                st.code(p, language="text")
