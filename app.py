import streamlit as st
import google.generativeai as genai
import time
import sys

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Microstock Engine", page_icon="🎨", layout="wide")

# --- CEK LIBRARY OTOMATIS (Jaga-jaga) ---
try:
    import google.generativeai as genai
    # Pastikan versi minimal terpenuhi
    ver = genai.__version__
    major, minor, patch = map(int, ver.split('.'))
    if minor < 7:
        st.error(f"⚠️ Versi Library Kuno ({ver}). Update 'requirements.txt' dengan: google-generativeai>=0.8.3")
        st.stop()
except ImportError:
    st.error("❌ Library belum terinstal. Cek requirements.txt!")
    st.stop()

# --- DEFINISI MODE VISUAL ---
VISUAL_MODES = {
    "1": {"name": "Isolated Object", "keywords": "white background, studio lighting, isolated on white, high quality, 8k", "ar": "--ar 1:1"},
    "2": {"name": "Copy Space", "keywords": "minimalist, wide shot, rule of thirds, negative space on the side, clean composition", "ar": "--ar 16:9"},
    "3": {"name": "Social Media Aesthetic", "keywords": "top down view, knolling, aesthetic lighting, instagram style, flatlay, soft shadows", "ar": "--ar 4:5"},
    "4": {"name": "Line Art / Doodle", "keywords": "thick outline, black and white, coloring book style, sticker design, vector style, simple", "ar": "--ar 1:1"},
    "5": {"name": "Isometric 3D", "keywords": "isometric view, 3d vector render, gradient glass texture, tech startup vibe, cute 3d", "ar": "--ar 16:9"}
}

# --- MANAJEMEN API KEY (INPUT MANUAL LANGSUNG) ---
if 'my_api_keys' not in st.session_state:
    st.session_state.my_api_keys = []

st.sidebar.header("🔑 API Key Setup")
st.sidebar.info("Masukkan 10 Key Anda di sini. Langsung Copy-Paste semua.")

# Input Area
raw_input = st.sidebar.text_area(
    "Paste Key (Pisahkan koma atau baris baru)", 
    height=150,
    placeholder="AIzaSyKeySatu...\nAIzaSyKeyDua...\nAIzaSyKeyTiga...",
    help="Key akan otomatis disimpan sementara."
)

if raw_input:
    # Membersihkan input (Ganti baris baru jadi koma, lalu pisahkan koma)
    cleaned = [k.strip() for k in raw_input.replace('\n', ',').split(',') if k.strip()]
    # Validasi sederhana (Key Google biasanya mulai dengan AIza)
    valid_keys = [k for k in cleaned if k.startswith("AIza")]
    
    if valid_keys:
        st.session_state.my_api_keys = valid_keys
        st.sidebar.success(f"✅ {len(valid_keys)} Key Valid Terbaca!")
    else:
        st.sidebar.error("❌ Format Key salah. Harus berawalan 'AIza'.")

API_KEYS = st.session_state.my_api_keys

# --- GENERATOR ENGINE ---
def run_generator(topic, mode_key, trend, qty):
    mode = VISUAL_MODES[mode_key]
    results = []
    
    # UI Progress
    log_expander = st.expander("📜 Log Proses (Buka untuk melihat detail)", expanded=True)
    progress_bar = st.progress(0)
    
    key_idx = 0
    
    # Model Priority (Flash -> Pro)
    MODELS = ["gemini-1.5-flash", "gemini-1.5-flash-latest", "gemini-pro"]
    
    for i in range(qty):
        success = False
        attempts = 0
        
        # Loop Key Rotation
        while not success and attempts < len(API_KEYS):
            current_key = API_KEYS[key_idx]
            masked_key = f"{current_key[:5]}...{current_key[-4:]}"
            
            genai.configure(api_key=current_key)
            
            # Loop Model Fallback
            for model_name in MODELS:
                try:
                    model = genai.GenerativeModel(model_name)
                    
                    prompt_text = f"""
                    Role: Expert Midjourney Prompter.
                    Task: Create 1 prompt for Topic: "{topic}".
                    Style: {mode['name']} {trend}.
                    Mandatory Params: {mode['keywords']} {mode['ar']} --v 6.0
                    
                    Constraint: Output ONLY the prompt text. No JSON. No Intro.
                    """
                    
                    response = model.generate_content(prompt_text)
                    
                    # Bersihkan hasil
                    final_text = response.text.strip().replace('"', '').replace('`', '')
                    if "json" in final_text: final_text = final_text.replace("json", "")
                    
                    if len(final_text) > 5:
                        results.append(final_text)
                        log_expander.success(f"✅ Prompt #{i+1} OK (Key: {masked_key})")
                        success = True
                        break # Keluar loop model
                        
                except Exception as e:
                    err = str(e)
                    # Jika Limit (429) -> Ganti Key
                    if "429" in err:
                        log_expander.warning(f"⚠️ Key {masked_key} Limit Habis. Ganti key...")
                        break # Break loop model, lanjut loop key
                    # Jika Key Salah (400) -> Catat error fatal
                    elif "400" in err or "API key not valid" in err:
                        log_expander.error(f"❌ Key Invalid: {masked_key}. Cek copy-paste Anda.")
                        break
                    # Jika Model Not Found (404) -> Coba model berikutnya
                    elif "404" in err:
                        continue 
                    else:
                        continue

            if success:
                key_idx = (key_idx + 1) % len(API_KEYS)
                time.sleep(1) # Jeda aman
                break
            else:
                key_idx = (key_idx + 1) % len(API_KEYS)
                attempts += 1
        
        if not success:
            st.error(f"❌ Gagal total pada prompt #{i+1}. Semua key sibuk/error.")
            break
            
        progress_bar.progress((i + 1) / qty)
        
    return results

# --- UI UTAMA ---
st.title("🎨 Microstock Prompt Engine")
st.markdown("---")

col1, col2 = st.columns(2)
with col1:
    topic = st.text_input("💡 Topik", "Chinese New Year Fire Horse")
    mode = st.selectbox("🎨 Mode", list(VISUAL_MODES.keys()), format_func=lambda x: VISUAL_MODES[x]['name'])
with col2:
    trend = st.text_input("📈 Trend", "")
    qty = st.number_input("🔢 Jumlah", 1, 100, 5)

if st.button("🚀 Generate Prompts", type="primary"):
    if not API_KEYS:
        st.error("⚠️ Masukkan API Key dulu di Sidebar (Kiri)!")
    else:
        res = run_generator(topic, mode, trend, qty)
        
        if res:
            st.success("Selesai!")
            
            # Download
            txt_file = "\n\n".join([f"{i+1}. {p}" for i,p in enumerate(res)])
            st.download_button("📥 Download .txt", txt_file, "prompts.txt")
            
            st.markdown("---")
            for i, p in enumerate(res):
                st.write(f"**Prompt #{i+1}**")
                st.code(p, language="text")
