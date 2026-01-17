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

# --- LOGIKA API KEY (SECRETS) ---
# Cek apakah ada API Key tersimpan di Secrets Streamlit
if "api_keys" in st.secrets:
    API_KEYS = st.secrets["api_keys"]
    st.sidebar.success(f"✅ Terhubung: {len(API_KEYS)} API Key dimuat dari Cloud.")
else:
    # Jika tidak ada di secrets, minta manual (opsional)
    st.sidebar.warning("⚠️ Belum ada API Key di Secrets.")
    api_input = st.sidebar.text_area("Input Manual API Keys (Satu per baris)")
    API_KEYS = [k.strip() for k in api_input.split('\n') if k.strip()]

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
        "keywords": "50 keywords (English, comma separated)",
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
        status_text.text(f"⏳ Membuat aset ke-{i+1}...")
        success = False
        while not success and key_index < len(API_KEYS):
            current_key = API_KEYS[key_index]
            try:
                model = get_model(current_key)
                prompt = create_system_prompt(topic, mode_data, trend)
                response = model.generate_content(prompt)
                data = json.loads(response.text)
                results.append(data)
                success = True
                time.sleep(1)
            except Exception:
                key_index += 1 
        
        if not success:
            st.error("❌ API Key habis/error!")
            break
        progress_bar.progress((i + 1) / qty)
        
    status_text.empty()
    return results

# --- UI UTAMA ---
st.title("🎨 AI Microstock Engine")
col1, col2 = st.columns(2)
with col1:
    topic = st.text_input("💡 Topik", placeholder="Misal: Imlek Kuda Api")
    mode_key = st.selectbox("🎨 Mode", list(VISUAL_MODES.keys()), format_func=lambda x: VISUAL_MODES[x]['name'])
with col2:
    trend = st.text_input("📈 Trend (Opsional)")
    qty = st.number_input("Jumlah", 1, 50, 5)

if st.button("🚀 Generate", type="primary"):
    if not API_KEYS:
        st.error("API Key belum disetting!")
    elif not topic:
        st.error("Topik kosong!")
    else:
        with st.spinner("Sedang berpikir..."):
            data = run_generation(topic, mode_key, trend, qty)
            if data:
                df = pd.DataFrame(data)
                st.dataframe(df)
                st.download_button("📥 Download CSV", df.to_csv(index=False).encode('utf-8'), f"microstock_{topic}.csv", "text/csv")
                for d in data:
                    with st.expander(f"Prompt: {d['title']}"):
                        st.code(d['midjourney_prompt'])