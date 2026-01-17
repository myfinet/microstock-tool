import streamlit as st
import google.generativeai as genai
import time
import sys

# --- 1. SETUP & CEK LIBRARY ---
st.set_page_config(page_title="Microstock Engine Fix", page_icon="🚑", layout="wide")

try:
    import google.generativeai as genai
    ver = genai.__version__
    # Cek versi library
    if int(ver.split('.')[1]) < 7:
        st.error(f"❌ Versi Library Kuno: {ver}. Wajib update requirements.txt ke >=0.8.3")
except:
    st.error("❌ Library google-generativeai tidak terinstal.")

# --- 2. INPUT & PEMBERSIH KEY (CRITICAL FIX) ---
st.sidebar.header("🔑 Input API Key")
st.sidebar.info("Paste 10 Key Anda di bawah (Format apapun: pakai koma, enter, atau kutip tidak masalah).")

raw_input = st.sidebar.text_area("Paste Keys Disini:", height=200)

VALID_KEYS = []

if raw_input:
    # LANGKAH PEMBERSIHAN EKSTREM
    # 1. Ganti baris baru jadi koma
    temp = raw_input.replace('\n', ',')
    # 2. Pisahkan berdasarkan koma
    parts = temp.split(',')
    
    st.sidebar.markdown("---")
    st.sidebar.write("🔍 **Hasil Scan Key:**")
    
    for i, p in enumerate(parts):
        # 3. Hapus spasi kiri/kanan
        clean_k = p.strip()
        # 4. Hapus tanda kutip ganda dan tunggal (INI YANG SERING BIKIN ERROR)
        clean_k = clean_k.replace('"', '').replace("'", "")
        
        if len(clean_k) > 30 and clean_k.startswith("AIza"):
            VALID_KEYS.append(clean_k)
            # Tampilkan indikator visual (4 huruf awal...4 huruf akhir)
            st.sidebar.success(f"Key #{i+1}: {clean_k[:5]}...{clean_k[-4:]} (OK)")
        elif len(clean_k) > 5:
            st.sidebar.error(f"Key #{i+1}: Format Salah (Bukan AIza...)")

    if VALID_KEYS:
        st.sidebar.success(f"✅ Total {len(VALID_KEYS)} Key Bersih Siap Pakai!")
    else:
        st.sidebar.warning("⚠️ Belum ada key valid terbaca.")

# --- 3. LOGIKA GENERATOR ---
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
    
    # Debug Container
    log = st.expander("📜 Log Detil (Wajib buka jika error)", expanded=True)
    pbar = st.progress(0)
    
    key_idx = 0
    
    # Model List (Prioritaskan Flash)
    MODELS = ["gemini-1.5-flash", "gemini-1.5-flash-latest", "gemini-pro"]

    for i in range(qty):
        success = False
        attempts = 0
        
        while not success and attempts < len(VALID_KEYS):
            # Ambil key & masking untuk log
            current_key = VALID_KEYS[key_idx]
            masked = f"{current_key[:5]}...{current_key[-4:]}"
            
            genai.configure(api_key=current_key)
            
            for model_name in MODELS:
                try:
                    model = genai.GenerativeModel(model_name)
                    prompt = f"Create 1 Midjourney prompt for '{topic}', style '{mode['name']}'. mandatory: {mode['keywords']} {mode['ar']}. Output raw text only."
                    
                    response = model.generate_content(prompt)
                    
                    if response.text:
                        clean_text = response.text.replace('`','').replace('"prompt":','').strip()
                        results.append(clean_text)
                        log.success(f"✅ Prompt #{i+1} Berhasil (Key: {masked})")
                        success = True
                        break # Break loop model
                        
                except Exception as e:
                    err = str(e)
                    if "429" in err:
                        log.warning(f"⚠️ Key {masked} Limit Habis. Ganti Key.")
                        break # Ganti key
                    elif "400" in err:
                        log.error(f"❌ Key {masked} INVALID/RUSAK. Hapus key ini.")
                        break # Ganti key
                    elif "404" in err:
                        continue # Coba model lain
                    else:
                        log.error(f"❌ Error Asli: {err}")
                        break
            
            # Rotasi Key
            key_idx = (key_idx + 1) % len(VALID_KEYS)
            
            if success:
                time.sleep(1)
                break
            else:
                attempts += 1
                time.sleep(1)
        
        if not success:
            st.error(f"❌ Gagal Total pada Prompt #{i+1}. Semua key dicoba dan gagal.")
            break
            
        pbar.progress((i+1)/qty)
        
    return results

# --- 4. UI ---
st.title("🚑 Microstock Engine (Fix)")
st.markdown("---")

col1, col2 = st.columns(2)
with col1:
    topic = st.text_input("Topik", "Chinese New Year")
    mode = st.selectbox("Mode", list(VISUAL_MODES.keys()))
with col2:
    trend = st.text_input("Trend", "")
    qty = st.number_input("Jumlah", 1, 100, 5)

if st.button("🚀 Generate Now", type="primary"):
    if not VALID_KEYS:
        st.error("Masukkan Key di Sidebar dulu sampai muncul tanda centang hijau!")
    else:
        res = run_gen(topic, mode, trend, qty)
        if res:
            st.success("Selesai!")
            # Download
            txt = "\n\n".join([f"{i+1}. {p}" for i,p in enumerate(res)])
            st.download_button("📥 Download TXT", txt, "prompts.txt")
            # Show
            for idx, p in enumerate(res):
                st.write(f"**#{idx+1}**")
                st.code(p, language="text")
