import streamlit as st
import google.generativeai as genai
import sys

st.set_page_config(page_title="FINAL FIX", page_icon="🛠️", layout="wide")

st.title("🛠️ Microstock Engine (REST Mode)")
st.info("Mode ini menggunakan protokol HTTP standar agar tembus firewall Streamlit.")

# --- 1. SETUP MANUAL ---
st.sidebar.header("🔑 Setup Key")
raw_keys = st.sidebar.text_area("Paste 10 Key Anda (Copy Semua sekaligus):", height=200)

# Pembersih Key Super Agresif
CLEAN_KEYS = []
if raw_keys:
    # Ganti enter jadi koma, pisah koma, hapus spasi, hapus kutip
    candidates = raw_keys.replace('\n', ',').split(',')
    for c in candidates:
        k = c.strip().replace('"', '').replace("'", "")
        if k.startswith("AIza") and len(k) > 30:
            CLEAN_KEYS.append(k)

    if CLEAN_KEYS:
        st.sidebar.success(f"✅ {len(CLEAN_KEYS)} Key Valid Terbaca!")
    else:
        st.sidebar.error("❌ Tidak ada key yang valid (Harus mulai dengan 'AIza')")

# --- 2. GENERATOR LOGIC (DENGAN TRANSPORT='REST') ---
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
    log = st.expander("Logs", expanded=True)
    pbar = st.progress(0)
    key_idx = 0
    
    # Model Target
    model_name = "gemini-1.5-flash"

    for i in range(qty):
        success = False
        attempts = 0
        
        while not success and attempts < len(CLEAN_KEYS):
            current_key = CLEAN_KEYS[key_idx]
            masked = f"...{current_key[-4:]}"
            
            try:
                # --- RAHASIA SUKSES DI SINI: transport='rest' ---
                genai.configure(api_key=current_key, transport='rest')
                
                model = genai.GenerativeModel(model_name)
                
                # Prompt sangat sederhana untuk menghindari filter
                prompt = f"Create 1 Midjourney prompt for: {topic}. Style: {mode['name']}. No intro."
                
                response = model.generate_content(prompt)
                
                if response.text:
                    res_text = response.text.strip().replace('"','').replace('*','')
                    results.append(res_text)
                    log.success(f"✅ Prompt #{i+1} OK (Key: {masked})")
                    success = True
            
            except Exception as e:
                err = str(e)
                if "429" in err:
                    log.warning(f"⚠️ Limit (Key: {masked})")
                elif "400" in err:
                    log.error(f"❌ INVALID KEY (Key: {masked}). Cek Key ini!")
                else:
                    log.error(f"❌ Error (Key: {masked}): {err}")
            
            # Rotasi Key
            key_idx = (key_idx + 1) % len(CLEAN_KEYS)
            
            if success:
                break
            else:
                attempts += 1
        
        if not success:
            st.error(f"Gagal Prompt #{i+1}")
            break
        
        pbar.progress((i+1)/qty)
        
    return results

# --- 3. UI ---
col1, col2 = st.columns(2)
with col1:
    topic = st.text_input("Topik", "Cat")
    mode = st.selectbox("Mode", list(VISUAL_MODES.keys()))
with col2:
    trend = st.text_input("Trend")
    qty = st.number_input("Jml", 1, 10, 1)

if st.button("🚀 GENERATE"):
    if not CLEAN_KEYS:
        st.error("Masukkan Key di Sidebar dulu!")
    else:
        res = run_gen(topic, mode, trend, qty)
        if res:
            st.success("Selesai!")
            for idx, p in enumerate(res):
                st.write(f"**#{idx+1}**")
                st.code(p, language="text")
