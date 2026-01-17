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
    key_idx = 0
    
    # Cache model name agar tidak search terus
    active_model_name = None

    for i in range(qty):
        success = False
        attempts = 0
        
        while not success and attempts < len(CLEAN_KEYS):
            current_key = CLEAN_KEYS[key_idx]
            masked = f"...{current_key[-4:]}"
            
            try:
                # 1. Cari Model dulu jika belum ketemu
                if not active_model_name:
                    found = get_available_model(current_key)
                    if found:
                        active_model_name = found
                        log.info(f"🧠 Menggunakan Model: {active_model_name}")
                    else:
                        active_model_name = "models/gemini-pro"

                # 2. Konfigurasi
                genai.configure(api_key=current_key, transport='rest')
                model = genai.GenerativeModel(active_model_name)
                
                # 3. Generate
                prompt = f"Create 1 Midjourney prompt for: {topic}. Style: {mode['name']}. No intro."
                response = model.generate_content(prompt)
                
                if response.text:
                    res_text = response.text.strip().replace('"','').replace('*','')
                    results.append(res_text)
                    log.success(f"✅ Prompt #{i+1} OK (Key: {masked})")
                    success = True
            
            except Exception as e:
                err = str(e)
                if "404" in err:
                    # Model salah, reset cache model biar cari lagi
                    active_model_name = None 
                    log.warning("⚠️ Model not found, mencari ulang...")
                elif "429" in err:
                    log.warning(f"⚠️ Limit (Key: {masked})")
                else:
                    log.error(f"❌ Error (Key: {masked}): {err}")
            
            key_idx = (key_idx + 1) % len(CLEAN_KEYS)
            
            if success: break
            else: attempts += 1
        
        if not success:
            st.error(f"Gagal Prompt #{i+1}")
            break
        
        pbar.progress((i+1)/qty)
        
    return results

# --- UI ---
col1, col2 = st.columns(2)
with col1:
    topic = st.text_input("Topik", "Cat")
    mode = st.selectbox("Mode", list(VISUAL_MODES.keys()))
with col2:
    trend = st.text_input("Trend")
    qty = st.number_input("Jml", 1, 10, 1)

if st.button("🚀 GENERATE"):
    if not CLEAN_KEYS:
        st.error("Masukkan Key di Sidebar!")
    else:
        res = run_gen(topic, mode, trend, qty)
        if res:
            st.success("Selesai!")
            for idx, p in enumerate(res):
                st.write(f"**#{idx+1}**")
                st.code(p, language="text")
