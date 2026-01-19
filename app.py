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
    st.session_state.app_keys = []

raw_input = st.sidebar.text_area("API Keys:", height=150, placeholder="AIzaSy...")

if raw_input:
    keys = clean_keys(raw_input)
    if keys:
        st.session_state.app_keys = keys
        st.sidebar.success(f"✅ {len(keys)} Key Ready")
        mod = get_best_model(keys[0])
        st.sidebar.caption(f"Engine: {mod}")
    else:
        st.sidebar.error("❌ Key Invalid")

# ==========================================
# 5. UI UTAMA
# ==========================================
st.title("🎨 Microstock Generator (All-in-One)")
st.caption("Solusi lengkap: Aset PNG, Konten Viral, dan Layout Cetak.")

col1, col2 = st.columns(2)

with col1:
    topic = st.text_input("💡 Topik / Objek", placeholder="Contoh: Spa Treatment / Corporate Meeting")
    
    # PILIHAN KATEGORI UTAMA
    category = st.radio(
        "🎯 Target Output:",
        [
            "Object Slice (PNG Assets)", 
            "Social Media (IG/TikTok)",
            "Print Media (Flyer/Brochure)" # NEW
        ],
    )

with col2:
    # KONFIGURASI DINAMIS
    if category == "Object Slice (PNG Assets)":
        ar_mode = "--ar 1:1 (Square)"
        st.info("📦 **Mode Aset:** Background putih bersih, isolasi objek, siap crop.")
        
    elif category == "Social Media (IG/TikTok)":
        ar_mode = st.selectbox("📐 Rasio", ["--ar 9:16 (Reels/TikTok)", "--ar 4:5 (IG Feed)"])
        st.info("📱 **Mode Sosial:** Komposisi vertikal, aesthetic, mobile-friendly.")
        
    else: # Print Media
        ar_mode = st.selectbox("📐 Rasio", [
            "--ar 2:3 (Poster/Flyer Vertikal)", 
            "--ar 3:2 (Landscape/Banner)", 
            "--ar 4:3 (Majalah Standard)"
        ])
        st.info("🖨️ **Mode Cetak:** Fokus pada 'Negative Space' (Area Kosong) untuk penempatan Teks/Logo.")

    qty = st.slider("🔢 Jumlah Variasi (Max 10)", 1, 10, 5)

# ==========================================
# 6. GENERATOR ENGINE
# ==========================================
if st.button("🚀 Generate Prompts", type="primary"):
    keys = st.session_state.app_keys
    
    if not keys:
        st.error("⚠️ Masukkan Key di Sidebar!")
    elif not topic:
        st.warning("⚠️ Masukkan Topik!")
    else:
        results = []
        pbar = st.progress(0)
        status = st.empty()
        
        angles = get_angles(category, qty)
        
        key_idx = 0
        model_name = get_best_model(keys[0])
        
        for i in range(qty):
            angle = angles[i]
            status.text(f"⏳ Meracik Konsep {i+1}: {angle.split('(')[0]}...")
            
            success = False
            attempts = 0
            
            while not success and attempts < len(keys):
                current_key = keys[key_idx]
                
                try:
                    genai.configure(api_key=current_key, transport='rest')
                    model = genai.GenerativeModel(model_name)
                    
                    # SYSTEM PROMPT YANG DISESUAIKAN PER KATEGORI
                    if category == "Object Slice (PNG Assets)":
                        sys_prompt = f"""
                        Role: Technical Stock Photographer.
                        Task: Create 1 Midjourney prompt for Asset Creation.
                        Subject: {topic}. Angle: {angle}. AR: {ar_mode}.
                        MANDATORY: Pure white background (hex #ffffff), isolated object, no heavy shadows, clipping path friendly, 8k.
                        OUTPUT: Raw prompt text only.
                        """
                    elif category == "Social Media (IG/TikTok)":
                        sys_prompt = f"""
                        Role: Social Media Creator.
                        Task: Create 1 Viral Midjourney prompt.
                        Subject: {topic}. Vibe: {angle}. AR: {ar_mode}.
                        MANDATORY: Vertical framing, engaging, aesthetic lighting, instagrammable, clean composition.
                        OUTPUT: Raw prompt text only.
                        """
                    else: # Print Media
                        sys_prompt = f"""
                        Role: Commercial Advertising Photographer.
                        Task: Create 1 Midjourney prompt for Print Ad Layout.
                        Subject: {topic}. Composition: {angle}. AR: {ar_mode}.
                        MANDATORY: Generous NEGATIVE SPACE (Blank Space) for text placement, high resolution, magazine quality, soft lighting, professional layout.
                        OUTPUT: Raw prompt text only.
                        """
                    
                    response = model.generate_content(sys_prompt, safety_settings=SAFETY)
                    
                    if response.text:
                        clean_p = response.text.strip().replace('"', '').replace("`", "").replace("Prompt:", "")
                        results.append((angle.split('(')[0], clean_p))
                        success = True
                        
                except Exception:
                    pass
                
                key_idx = (key_idx + 1) % len(keys)
                
                if success:
                    time.sleep(0.5)
                    break
                else:
                    attempts += 1
                    time.sleep(1)
            
            pbar.progress((i+1)/qty)
        
        status.empty()
        
        if results:
            st.success(f"✅ Selesai! {len(results)} Prompt Spesifik.")
            
            # Download
            txt_out = ""
            for idx, r in enumerate(results):
                txt_out += f"[{r[0]}] {r[1]}\n\n"
            
            st.download_button("📥 Download .txt", txt_out, f"prompts_{topic}.txt")
            
            st.markdown("---")
            
            for idx, (ang, txt) in enumerate(results):
                st.markdown(f"**#{idx+1} {ang}**")
                st.code(txt, language="text")
        else:
            st.error("❌ Gagal. Cek Key.")
