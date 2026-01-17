import streamlit as st
import google.generativeai as genai
import time
from google.generativeai.types import HarmCategory, HarmBlockThreshold

# ==========================================
# 1. KONFIGURASI HALAMAN & STYLE
# ==========================================
st.set_page_config(
    page_title="Microstock Prompt Pro",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS untuk tampilan lebih rapi
st.markdown("""
<style>
    .stCodeBlock {margin-bottom: 0px;}
    .reportview-container {background: #0e1117;}
    div[data-testid="stExpander"] div[role="button"] p {font-size: 1rem; font-weight: bold;}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. LOGIKA UTAMA (ENGINE)
# ==========================================

# A. Pembersih Key Otomatis
def clean_api_keys(raw_text):
    if not raw_text: return []
    # Ubah baris baru jadi koma, pisah koma, hapus spasi & kutip
    candidates = raw_text.replace('\n', ',').split(',')
    cleaned = []
    for c in candidates:
        k = c.strip().replace('"', '').replace("'", "")
        # Validasi format dasar Google Key
        if k.startswith("AIza") and len(k) > 30:
            cleaned.append(k)
    return list(set(cleaned)) # Hapus duplikat

# B. Auto-Discovery Model (Anti-404)
# Mencari model terbaik yang tersedia di akun, menggunakan protokol REST
@st.cache_resource
def get_best_model(_api_key):
    try:
        # Wajib pakai REST agar tembus firewall Streamlit
        genai.configure(api_key=_api_key, transport='rest')
        
        models = list(genai.list_models())
        available = [m.name for m in models if 'generateContent' in m.supported_generation_methods]
        
        # Prioritas Model (Flash -> Pro -> Apapun yang ada)
        for m in available:
            if 'flash' in m and '1.5' in m: return m
        for m in available:
            if 'flash' in m: return m
        for m in available:
            if 'pro' in m and '1.5' in m: return m
            
        return available[0] if available else "models/gemini-1.5-flash"
    except:
        return "models/gemini-1.5-flash" # Fallback

# C. Konfigurasi Safety (Agar prompt tidak diblokir sensor)
SAFETY_SETTINGS = {
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
}

# ==========================================
# 3. SIDEBAR: SETUP API
# ==========================================
st.sidebar.header("🔑 API Configuration")
st.sidebar.caption("Paste API Key Anda di bawah ini (bisa sekaligus banyak).")

# Menggunakan Session State agar key tidak hilang saat refresh/klik tombol
if 'api_keys' not in st.session_state:
    st.session_state.api_keys = []

raw_input = st.sidebar.text_area("API Keys:", height=150, help="Format: AIzaSy...", placeholder="Paste daftar key di sini...")

if raw_input:
    keys = clean_api_keys(raw_input)
    if keys:
        st.session_state.api_keys = keys
        st.sidebar.success(f"✅ {len(keys)} Key Siap Digunakan")
        
        # Deteksi Model di background
        active_model = get_best_model(keys[0])
        st.sidebar.info(f"🧠 Engine: `{active_model.split('/')[-1]}`")
    else:
        st.sidebar.error("❌ Format Key tidak valid (Harus diawali 'AIza')")

# ==========================================
# 4. PRESET MODE VISUAL (Optimized for Stock)
# ==========================================
VISUAL_MODES = {
    "isolated": {
        "label": "📦 Isolated Object (Asset)",
        "desc": "White background, clean cut, no shadow, commercial use",
        "prompt": "isolated on plain white background, studio lighting, commercial photography, ultra detailed, 8k, sharp focus, no shadow, --ar 1:1"
    },
    "copyspace": {
        "label": "📝 Copy Space (Background)",
        "desc": "Wide shot, minimalist, room for text placement",
        "prompt": "minimalist composition, wide angle, negative space on the side for text, soft lighting, professional stock photo, high resolution, --ar 16:9"
    },
    "flatlay": {
        "label": "📸 Flatlay / Social Media",
        "desc": "Top-down view, organized items, aesthetic",
        "prompt": "knolling photography, flat lay, top down view, aesthetic arrangement, soft shadows, instagram style, trending on pinterest, --ar 4:5"
    },
    "vector": {
        "label": "🎨 Vector / Illustration",
        "desc": "Flat design, sticker style, simple lines",
        "prompt": "vector art style, flat design, thick outline, sticker design, white background, adobe illustrator style, simple and clean, --ar 1:1"
    },
    "3d_icon": {
        "label": "🧊 3D Icon / Isometric",
        "desc": "Cute 3D render, clay texture or glass",
        "prompt": "3d isometric icon, claymorphism, soft gradient lighting, cute 3d render, c4d, blender style, colorful, --ar 1:1"
    }
}

# ==========================================
# 5. UI UTAMA
