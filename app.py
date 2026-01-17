import streamlit as st
import google.generativeai as genai
import pandas as pd
import json
import time

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Microstock Engine", page_icon="🎨", layout="wide")

# --- DEFINISI MODE VISUAL ---
VISUAL_MODES = {
    "1": {"name": "Isolated Object (Siap Slice)", "keywords": "white background, studio lighting, no shadow, isolated on white", "ar": "--ar 1:1"},
    "2": {"name": "Copy Space (Space Iklan)", "keywords": "minimalist, wide shot, rule of thirds, negative space on the side", "ar": "--ar 16:9"},
    "3": {"name": "Social Media Aesthetic", "keywords": "top down view, knolling, aesthetic lighting, instagram style, flatlay", "ar": "--ar 4:5"},
    "4": {"name": "Doodle & Line Art", "keywords": "thick outline, black and white, coloring book style, sticker design, vector style", "ar": "--ar 1:1"},
    "5": {"name": "Infographic & Isometric", "keywords": "isometric view, 3d vector render, gradient glass texture, tech startup vibe, --no text letters", "ar": "--ar 16:9"}
}

# --- LOGIKA API KEY (HYBRID: SECRETS ATAU MANUAL) ---
st.sidebar.header("🔑 Konfigurasi API")

API_KEYS = []
raw_keys = ""

# 1. Cek apakah ada di Secrets (Prioritas Utama)
if "api_keys" in st.secrets:
    raw_keys = st.secrets["api_keys"]
    st.sidebar.success(f"✅ Menggunakan API Key dari Database Aman (Secrets).")
# 2. Jika tidak ada di Secrets, tampilkan Input Manual
else:
    st.sidebar.info("ℹ️ Masukkan API Key di bawah ini (pisahkan dengan koma jika lebih dari satu).")
    raw_keys = st.sidebar.text_area("API Keys", placeholder="Key1,Key2,Key3", help="Paste key Anda di sini. Satu baris dipisah koma.")

# Proses string menjadi list
if raw_keys:
    API_KEYS = [k.strip() for k in raw_keys.split(',') if k.strip()]
    if "api_keys" not in st.secrets:
        st.sidebar.success(f"✅ {len(API_KEYS)} Key siap digunakan.")

# --- FUNGSI GENERATOR ---
def get_model(api_key):
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(model_name="gemini-1.5-flash", generation_config={"response_mime_type": "application/json"})

def create_system_prompt(topic, mode_data, trend=""):
    return f"""
    Role: Microstock Expert. Task: Create asset data for Topic: "{topic}", Mode: "{mode_data['name']}", Trend: "{trend}".
    RETURN JSON ONLY:
    {{
        "midjourney_prompt": "Visual description + {mode_data['keywords']} + {mode_data['ar']} --v 6.0",
        "title": "SEO Title (English, Max 70 chars)",
        "keywords": "47 keywords (English, comma separated)",
        "social_caption": "Caption (Indonesian) + CTA",
        "hashtags": "#hashtags"
    }}
    """

def run_generation(topic, mode_key, trend, qty):
    mode_data = VISUAL_MODES[mode_key]
    results = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    key_index = 0
    
    for i in range(qty):
        status_text.text(f"⏳ Membuat aset ke-{i+1} dari {qty}...")
        success = False
        
        # Loop untuk mencoba key satu per satu jika error (Key Rotation)
        while not success and key_index < len(API_KEYS):
            current_key = API_KEYS[key_index]
            try:
                model = get_model(current_key)
                prompt = create_system_prompt(topic, mode_data, trend)
                response = model.generate_content(prompt)
                data = json.loads(response.text)
                results.append(data)
                success = True
                time.sleep(5) # Jeda aman
            except Exception as e:
                # Jika error, pindah ke key berikutnya
                print(f"Key index {key_index} error: {e}")
                key_index += 1 
        
        if not success:
            st.error("❌ Semua API Key habis atau error! Cek kuota atau input Anda.")
            break
            
        progress_bar.progress((i + 1) / qty)
        
    status_text.empty()
    return results

# --- UI UTAMA ---
st.title("🎨 AI Microstock Engine")
st.markdown("---")

col1, col2 = st.columns(2)
with col1:
    topic = st.text_input("💡 Topik", placeholder="Misal: Imlek Kuda Api")
    mode_key = st.selectbox("🎨 Mode Visual", list(VISUAL_MODES.keys()), format_func=lambda x: VISUAL_MODES[x]['name'])
with col2:
    trend = st.text_input("📈 Trend Injector (Opsional)", placeholder="Misal: Cyberpunk, Pastel")
    qty = st.number_input("🔢 Jumlah Variasi", 1, 100, 5)

if st.button("🚀 Generate Aset", type="primary"):
    if not API_KEYS:
        st.error("⚠️ API Key kosong! Masukkan key di sidebar sebelah kiri atau atur Secrets.")
    elif not topic:
        st.error("⚠️ Topik belum diisi!")
    else:
        with st.spinner("Sedang meracik prompt & metadata..."):
            data = run_generation(topic, mode_key, trend, qty)
            
            if data:
                # Tampilkan Preview Data Frame
                df = pd.DataFrame(data)
                st.success(f"Selesai! {len(data)} aset berhasil dibuat.")
                st.dataframe(df)
                
                # Tombol Download
                st.download_button(
                    label="📥 Download CSV Lengkap",
                    data=df.to_csv(index=False).encode('utf-8'),
                    file_name=f"microstock_{topic.replace(' ', '_')}.csv",
                    mime="text/csv"
                )
                
                # Preview Prompt Text
                st.markdown("### 📝 Quick Copy Prompts")
                for d in data:
                    with st.expander(f"Prompt: {d['title']}"):
                        st.code(d['midjourney_prompt'])
                        st.caption(f"Keywords: {d['keywords']}")

