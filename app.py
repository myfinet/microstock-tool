import streamlit as st
import time
import random

# ==========================================
# 1. SETUP & LIBRARY CHECK
# ==========================================
st.set_page_config(
    page_title="Microstock Generator All-in-One",
    page_icon="🎨",
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
    st.error("❌ Library Error. Pastikan requirements.txt berisi: google-generativeai>=0.8.3")
    st.stop()

# ==========================================
# 2. CORE FUNCTIONS (FIXED)
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

@st.cache_resource
def get_best_model(_api_key):
    try:
        genai.configure(api_key=_api_key, transport='rest')
        models = list(genai.list_models())
        available = [m.name for m in models if 'generateContent' in m.supported_generation_methods]
        for m in available: 
            if 'flash' in m and '1.5' in m: return m
        for m in available: 
            if 'pro' in m: return m
        return available[0] if available else "models/gemini-1.5-flash"
    except:
        return "models/gemini-1.5-flash"

SAFETY = {
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
}

# ==========================================
# 3. LOGIKA ANGLE (THE BRAIN)
# ==========================================

# Kategori 1: OBJECT SLICE (PNG)
ANGLES_SLICE = [
    "Front View (Symmetrical, clean)",
    "Isometric View (3D Icon style)",
    "Top Down / Flat Lay (Organized)",
    "Three-Quarter View (Product shot)",
    "Exploded View (Parts floating)",
    "Close-up Macro (Texture focus)",
    "Floating / Levitation (Dynamic)",
    "Knolling (Arranged grid)"
]

# Kategori 2: SOCIAL MEDIA (Vertical)
ANGLES_SOCIAL = [
    "POV Shot (First person view)",
    "Vertical Hero Shot (Low angle looking up)",
    "Lifestyle Candid (Human element)",
    "Phone Screen Context (Mockup style)",
    "Aesthetic Blur / Bokeh Background",
    "Motion Blur (Dynamic action)",
    "Mirror Selfie / Reflection",
    "Behind The Scenes (Messy aesthetic)"
]

# Kategori 3: PRINT MEDIA (Blank Space) - BARU!
# Fokus pada Rule of Thirds dan Negative Space
ANGLES_PRINT = [
    "Rule of Thirds (Subject Left, Space Right)",
    "Rule of Thirds (Subject Right, Space Left)",
    "Bottom Composition (Space on Top for Title)",
    "Wide Panoramic (Banner style)",
    "Minimalist Studio (Vast background)",
    "Corner Composition (Subject in corner)",
    "Selective Focus (Blurred foreground for text)",
    "Top Down with Center Copy Space"
]

def get_angles(category, qty):
    if category == "Object Slice (PNG Assets)":
        base = ANGLES_SLICE
    elif category == "Social Media (IG/TikTok)":
        base = ANGLES_SOCIAL
    else:
        base = ANGLES_PRINT
        
    if qty > len(base):
        return random.sample(base * 2, qty)
    return random.sample(base, qty)

# ==========================================
# 4. SIDEBAR
# ==========================================
st.sidebar.header("🎨 Generator Setup")

if 'app_keys' not in st.session_state:
