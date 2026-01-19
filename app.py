import streamlit as st
import time
import random

# ==========================================
# 1. SETUP & LIBRARY
# ==========================================
st.set_page_config(
    page_title="Microstock Gen (Complete)",
    page_icon="⚡",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .stCodeBlock {margin-bottom: 0px;}
    div[data-testid="stExpander"] {border: 1px solid #e0e0e0; border-radius: 8px;}
</style>
""", unsafe_allow_html=True)

try:
    import google.generativeai as genai
    from google.generativeai.types import HarmCategory, HarmBlockThreshold
except ImportError:
    st.error("❌ Library Error. Requirements: google-generativeai>=0.8.3")
    st.stop()

# ==========================================
# 2. FUNGSI VALIDASI
# ==========================================

def clean_keys(raw_text):
    if not raw_text: return []
    candidates = raw_text.replace('\n', ',').split(',')
    cleaned = []
    for c in candidates:
        k = c.strip().replace('"', '').replace("'", "")
        if k.startswith("AIza") and len(k) > 20:
            cleaned.append(k)
    return list(set(cleaned))

def check_key_health(api_key):
    """Cek Key DAN simpan nama model yang berhasil"""
    try:
        genai.configure(api_key=api_key, transport='rest')
        
        # Cari Model
        models = list(genai.list_models())
        found_model = None
        candidates = [m.name for m in models if 'generateContent' in m.supported_generation_methods]
        
        # Prioritas Model
        for m in candidates:
            if 'flash' in m and '1.5' in m: found_model = m; break
        if not found_model:
            for m in candidates:
                if 'pro' in m and '1.5' in m: found_model = m; break
        if not found_model and candidates:
            found_model = candidates[0]
            
        if not found_model: return False, "No Model Found", None

        # Test Ping
        model = genai.GenerativeModel(found_model)
        model.generate_content("Hi", generation_config={'max_output_tokens': 1})
        
        return True, "Active", found_model

    except Exception as e:
        err = str(e)
        if "429" in err: return False, "Quota Limit", None
        if "400" in err: return False, "Invalid Key", None
        return False, f"Error: {err[:15]}...", None

# ==========================================
# 3. SIDEBAR: VALIDASI
# ==========================================
st.sidebar.header("🔑 API Key Manager")

if 'active_keys_data' not in st.session_state:
    st.session_state.active_keys_data = []

raw_input = st.sidebar.text_area("Paste API Keys:", height=100, placeholder="AIzaSy...")

if st.sidebar.button("🔍 Validasi & Sync Model", type="primary"):
    candidates = clean_keys(raw_input)
    
    if not candidates:
        st.sidebar.error("❌ Key kosong.")
    else:
        valid_data = []
        progress_bar = st.sidebar.progress(0)
        status_text = st.sidebar.empty()
        
        st.sidebar.markdown("---")
        
        for i, key in enumerate(candidates):
            status_text.text(f"Cek Key {i+1}...")
            is_alive, msg, model_name = check_key_health(key)
            
            if is_alive:
                st.sidebar.success(f"Key {i+1}: OK")
                valid_data.append({'key': key, 'model': model_name})
            else:
                st.sidebar.error(f"Key {i+1}: {msg}")
            
            progress_bar.progress((i + 1) / len(candidates))
            
        st.session_state.active_keys_data = valid_data
        status_text.empty()
        
        if valid_data:
            st.sidebar.success(f"🎉 {len(valid_data)} Key Siap!")
        else:
            st.sidebar.error("💀 Semua Key Gagal.")

if st.session_state.active_keys_data:
    st.sidebar.info(f"🟢 {len(st.session_state.active_keys_data)} Key Aktif")

# ==========================================
# 4. LOGIKA UTAMA
# ==========================================

SAFETY = {
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
}

ANGLES_SLICE = ["Front View", "Isometric View", "Top Down / Flat Lay", "Three-Quarter View", "Exploded View", "Close-up Macro", "Floating / Levitation", "Knolling"]
ANGLES_SOCIAL = ["POV Shot", "Vertical Hero Shot", "Lifestyle Candid", "Phone Screen Context", "Aesthetic Blur", "Motion Blur", "Mirror Selfie", "Behind The Scenes"]
ANGLES_PRINT = ["Rule of Thirds", "Bottom Composition", "Wide Panoramic", "Minimalist Studio", "Corner Composition", "Selective Focus", "Top Down Center Space"]

def get_angles(category, qty):
    if category == "Object Slice (PNG Assets)": base = ANGLES_SLICE
    elif category == "Social Media (IG/TikTok)": base = ANGLES_SOCIAL
    else: base = ANGLES_PRINT
    if qty > len(base): return random.sample(base * 2, qty)
    return random.sample(base, qty)

# ==========================================
# 5. UI GENERATOR
# ==========================================
st.title("⚡ Microstock Gen (Verified)")

ai_platform = st.radio("🤖 Platform:", ["Midjourney v6", "Flux.1", "Ideogram 2.0"], horizontal=True)

col1, col2 = st.columns(2)
with col1:
    topic = st.text_input("💡 Topik", placeholder="Contoh: Fresh Croissant")
    category = st.radio("🎯 Kategori:", ["Object Slice (PNG Assets)", "Social Media (IG/TikTok)", "Print Media (Flyer)"])

with col2:
    if ai_platform == "Midjourney v6":
        if category == "Object Slice (PNG Assets)": ar_display = "--ar 1:1"
        elif category == "Social Media (IG
