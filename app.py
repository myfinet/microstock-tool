import streamlit as st
import time
import random

# ==========================================
# 1. SETUP & LIBRARY CHECK (THE STABLE BASE)
# ==========================================
st.set_page_config(
    page_title="Microstock Asset & Social",
    page_icon="✂️",
    layout="wide"
)

# Custom CSS untuk tampilan lebih bersih
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
# 2. CORE FUNCTIONS (JANGAN DIUBAH - SUDAH FIX)
# ==========================================

# A. Pembersih Key (Anti-Spasi/Kutip)
def clean_keys(raw_text):
    if not raw_text: return []
    candidates = raw_text.replace('\n', ',').split(',')
    cleaned = []
    for c in candidates:
        k = c.strip().replace('"', '').replace("'", "")
        if k.startswith("AIza") and len(k) > 20:
            cleaned.append(k)
    return list(set(cleaned))

# B. Auto-Model Discovery (Anti-404)
@st.cache_resource
def get_best_model(_api_key):
    try:
        genai.configure(api_key=_api_key, transport='rest') # Wajib REST
        models = list(genai.list_models())
        available = [m.name for m in models if 'generateContent' in m.supported_generation_methods]
        
        # Prioritas: Flash -> Pro
        for m in available: 
            if 'flash' in m and '1.5' in m: return m
        for m in available: 
            if 'pro' in m: return m
        return available[0] if available else "models/gemini-1.5-flash"
    except:
        return "models/gemini-1.5-flash"

# C. Safety Settings (Anti-Block)
SAFETY = {
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
}

# ==========================================
# 3. LOGIKA SPESIFIK (ASSET VS SOCIAL)
# ==========================================

# Kategori 1: OBJECT SLICE (Untuk Aset PNG)
# Angle difokuskan pada "View" teknis agar mudah di-crop
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

# Kategori 2: SOCIAL MEDIA (IG/TikTok)
# Angle difokuskan pada "Experience" dan "Vertical Composition"
ANGLES_SOCIAL = [
    "POV Shot (First person view, hands visible)",
    "Behind The Scenes (Messy but aesthetic)",
    "Vertical Hero Shot (Low angle looking up)",
    "Lifestyle Candid (Human element)",
    "Phone Screen Mockup (Contextual)",
    "Aesthetic Blur / Bokeh (Background focus)",
    "Motion Blur (Action/Dynamic)",
    "Mirror Selfie / Reflection style"
]

def get_angles(category, qty):
    base_list = ANGLES_SLICE if category == "Object Slice (PNG Assets)" else ANGLES_SOCIAL
    if qty > len(base_list):
        return random.sample(base_list * 2, qty)
    return random.sample(base_list, qty)

# ==========================================
# 4. SIDEBAR SETUP
# ==========================================
st.sidebar.header("✂️ Asset Factory")

if 'asset_keys' not in st.session_state:
    st.session_state.asset_keys = []

raw_input = st.sidebar.text_area("API Keys:", height=150, placeholder="AIzaSy...")

if raw_input:
    keys = clean_keys(raw_input)
    if keys:
        st.session_state.asset_keys = keys
        st.sidebar.success(f"✅ {len(keys)} Key Ready")
        mod = get_best_model(keys[0])
        st.sidebar.caption(f"Engine: {mod}")
    else:
        st.sidebar.error("❌ Key Invalid")

# ==========================================
# 5. UI UTAMA
# ==========================================
st.title("✂️ Microstock Asset & Social Gen")
st.caption("Spesialisasi: Isolated Objects (untuk Freepik/Adobe) & Vertical Content (untuk Reels/TikTok).")

col1, col2 = st.columns(2)

with col1:
    # INPUT UTAMA
    topic = st.text_input("💡 Topik / Objek", placeholder="Contoh: Fresh Burger / Gaming Setup")
    
    # PILIHAN FOKUS (Target Market)
    category = st.radio(
        "🎯 Target Output:",
        ["Object Slice (PNG Assets)", "Social Media (IG/TikTok)"],
        horizontal=True
    )

with col2:
    # SETTING OTOMATIS BERDASARKAN KATEGORI
    if category == "Object Slice (PNG Assets)":
        ar_mode = "--ar 1:1 (Square)"
        st.info("ℹ️ **Mode Aset:** Prompt akan dimaksimalkan untuk background putih bersih, tanpa bayangan keras, siap potong (Cutout).")
    else:
        ar_mode = st.selectbox("📐 Aspect Ratio", ["--ar 9:16 (Reels/TikTok)", "--ar 4:5 (IG Feed)"])
        st.info("ℹ️ **Mode Sosial:** Prompt akan dimaksimalkan untuk komposisi vertikal, *aesthetic*, dan *engaging*.")

    qty = st.slider("🔢 Jumlah Variasi (Max 10)", 1, 10, 5)

# ==========================================
# 6. GENERATOR ENGINE
# ==========================================
if st.button("🚀 Generate Optimized Prompts", type="primary"):
    keys = st.session_state.asset_keys
    
    if not keys:
        st.error("⚠️ Masukkan Key di Sidebar!")
    elif not topic:
        st.warning("⚠️ Masukkan Topik!")
    else:
        results = []
        pbar = st.progress(0)
        status = st.empty()
        
        # Ambil Angle sesuai kategori
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
                    
                    # SYSTEM PROMPT (Sangat Spesifik)
                    if category == "Object Slice (PNG Assets)":
                        sys_prompt = f"""
                        Role: Technical Stock Photographer (Asset Creator).
                        Task: Create 1 Midjourney prompt for a High-Quality Asset.
                        
                        INPUTS:
                        - Subject: {topic}
                        - View/Angle: {angle}
                        - AR: {ar_mode}
                        
                        MANDATORY RULES FOR ASSETS:
                        1. BACKGROUND: Pure white background (hex #ffffff), studio lighting.
                        2. ISOLATION: Isolated, no heavy shadows, sharp edges, clipping path friendly.
                        3. QUALITY: 8k, hyper-detailed texture, commercial product photography.
                        4. DIVERSITY: Focus strictly on the Angle '{angle}'.
                        5. OUTPUT: Raw prompt text only. No intro.
                        """
                    else: # Social Media
                        sys_prompt = f"""
                        Role: Social Media Content Creator.
                        Task: Create 1 Viral Midjourney prompt for Reels/TikTok.
                        
                        INPUTS:
                        - Subject: {topic}
                        - Vibe/Angle: {angle}
                        - AR: {ar_mode}
                        
                        MANDATORY RULES FOR SOCIAL:
                        1. COMPOSITION: Vertical framing, mobile-first design, room for text overlays (copy space).
                        2. VIBE: Aesthetic, trending, cinematic lighting, engaging, high retention.
                        3. QUALITY: 8k, sharp focus, instagrammable.
                        4. DIVERSITY: Focus strictly on the Vibe '{angle}'.
                        5. OUTPUT: Raw prompt text only. No intro.
                        """
                    
                    response = model.generate_content(sys_prompt, safety_settings=SAFETY)
                    
                    if response.text:
                        clean_p = response.text.strip().replace('"', '').replace("`", "").replace("Prompt:", "")
                        results.append((angle.split('(')[0], clean_p))
                        success = True
                        
                except Exception:
                    pass # Silent failover
                
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
            st.success(f"✅ Selesai! {len(results)} Prompt Spesifik Dibuat.")
            
            # Download TXT
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
