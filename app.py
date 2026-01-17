import streamlit as st
import google.generativeai as genai
import json
import time

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Microstock Prompt Lite", page_icon="⚡", layout="wide")

# --- DEFINISI MODE VISUAL ---
VISUAL_MODES = {
    "1": {"name": "Isolated Object (Siap Slice)", "keywords": "white background, studio lighting, no shadow, isolated on white", "ar": "--ar 1:1"},
    "2": {"name": "Copy Space (Space Iklan)", "keywords": "minimalist, wide shot, rule of thirds, negative space on the side", "ar": "--ar 16:9"},
    "3": {"name": "Social Media Aesthetic", "keywords": "top down view, knolling, aesthetic lighting, instagram style, flatlay", "ar": "--ar 4:5"},
    "4": {"name": "Doodle & Line Art", "keywords": "thick outline, black and white, coloring book style, sticker design, vector style", "ar": "--ar 1:1"},
    "5": {"name": "Infographic & Isometric", "keywords": "isometric view, 3d vector render, gradient glass texture, tech startup vibe, --no text letters", "ar": "--ar 16:9"}
}

# --- LOGIKA API KEY (HYBRID) ---
st.sidebar.header("⚡ Konfigurasi API")
API_KEYS = []
raw_keys = ""

# Prioritas 1: Ambil dari Secrets Cloud
if "api_keys" in st.secrets:
    raw_keys = st.secrets["api_keys"]
    st.sidebar.success(f"✅ Menggunakan {len(raw_keys.split(','))} Key dari Cloud.")
# Prioritas 2: Input Manual
else:
    st.sidebar.info("Masukkan API Key (pisahkan koma).")
    raw_keys = st.sidebar.text_area("API Keys", placeholder="Key1,Key2,Key3")

if raw_keys:
    # Membersihkan spasi dan memisahkan koma
    API_KEYS = [k.strip() for k in raw_keys.split(',') if k.strip()]

# --- FUNGSI GENERATOR ---
def get_model(api_key):
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(model_name="gemini-1.5-flash", generation_config={"response_mime_type": "application/json"})

def create_lite_prompt(topic, mode_data, trend=""):
    # Prompt super pendek agar hemat & cepat
    return f"""
    Task: Create 1 Midjourney prompt.
    Topic: "{topic}"
    Style: "{mode_data['name']}" + {trend}
    Mandatory Params: {mode_data['keywords']} {mode_data['ar']} --v 6.0
    
    RETURN JSON ONLY: {{ "prompt": "Your_Prompt_Here" }}
    """

def run_generation(topic, mode_key, trend, qty):
    mode_data = VISUAL_MODES[mode_key]
    results = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    key_index = 0
    
    for i in range(qty):
        status_text.text(f"⚡ Generating prompt {i+1}/{qty}...")
        success = False
        
        while not success and key_index < len(API_KEYS):
            current_key = API_KEYS[key_index]
            try:
                model = get_model(current_key)
                sys_prompt = create_lite_prompt(topic, mode_data, trend)
                response = model.generate_content(sys_prompt)
                
                data = json.loads(response.text)
                
                # Bersihkan format jika ada sisa '/imagine'
                clean_prompt = data['prompt'].replace('/imagine prompt:', '').strip()
                results.append(clean_prompt)
                
                success = True
                time.sleep(5) # Jeda ringan
            except Exception:
                key_index += 1 # Ganti key jika error
        
        if not success:
            st.error("❌ Semua API Key limit/habis. Tambahkan key baru.")
            break
            
        progress_bar.progress((i + 1) / qty)
        
    status_text.empty()
    return results

# --- UI UTAMA ---
st.title("⚡ Microstock Prompt Lite")
st.markdown("---")

col1, col2 = st.columns(2)
with col1:
    topic = st.text_input("💡 Topik", placeholder="Misal: Imlek Kuda Api")
    mode_key = st.selectbox("🎨 Mode Visual", list(VISUAL_MODES.keys()), format_func=lambda x: VISUAL_MODES[x]['name'])
with col2:
    trend = st.text_input("📈 Trend (Opsional)", placeholder="Misal: Cyberpunk")
    qty = st.number_input("🔢 Jumlah", 1, 100, 5)

if st.button("🚀 Generate Prompts", type="primary"):
    if not API_KEYS:
        st.error("⚠️ API Key kosong!")
    elif not topic:
        st.error("⚠️ Topik harus diisi!")
    else:
        with st.spinner("Sedang memproses..."):
            prompts = run_generation(topic, mode_key, trend, qty)
            
            if prompts:
                st.success(f"Selesai! {len(prompts)} prompt berhasil dibuat.")
                
                # --- BAGIAN DOWNLOAD FILE ---
                # Kita format stringnya agar rapi saat didownload (pakai nomor)
                txt_content = ""
                for idx, p in enumerate(prompts, 1):
                    txt_content += f"{idx}. {p}\n\n"
                
                st.download_button(
                    label="📥 Download File .txt",
                    data=txt_content,
                    file_name=f"prompts_{topic.replace(' ', '_')}.txt",
                    mime="text/plain"
                )
                
                st.markdown("---")
                st.markdown("### 📋 Hasil (Klik icon 'copy' di pojok kanan kotak)")

                # --- BAGIAN TAMPILAN 1 BLOK 1 TOMBOL COPY ---
                for idx, p in enumerate(prompts, 1):
                    # Menulis label nomor
                    st.write(f"**Prompt #{idx}**")
                    # Menulis code block (ini otomatis ada tombol copynya di Streamlit)
                    st.code(p, language="text")
