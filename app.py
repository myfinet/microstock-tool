import streamlit as st
import time
import random

# ==========================================
# 1. SETUP & LIBRARY CHECK
# ==========================================
st.set_page_config(
    page_title="Microstock Multi-Engine",
    page_icon="⚡",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .stCodeBlock {margin-bottom: 0px;}
    div[data-testid="stExpander"] {border: 1px solid #e0e0e0; border-radius: 8px;}
    .stRadio [role=radiogroup] {gap: 20px;}
</style>
""", unsafe_allow_html=True)

try:
    import google.generativeai as genai
    from google.generativeai.types import HarmCategory, HarmBlockThreshold
except ImportError:
    st.error("❌ Library Error. Pastikan requirements.txt berisi: google-generativeai>=0.8.3")
    st.stop()

# ==========================================
# 2. CORE FUNCTIONS
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
# 3. LOGIKA ANGLE & KATEGORI
# ==========================================

# Kategori 1: OBJECT SLICE (PNG)
ANGLES_SLICE = [
    "Front View (Symmetrical)",
    "Isometric View (3D Icon style)",
    "Top Down / Flat Lay",
    "Three-Quarter View (Product shot)",
    "Exploded View (Parts floating)",
    "Close-up Macro (Texture focus)",
    "Floating / Levitation",
    "Knolling (Arranged grid)"
]

# Kategori 2: SOCIAL MEDIA (Vertical)
ANGLES_SOCIAL = [
    "POV Shot (First person view)",
    "Vertical Hero Shot (Low angle)",
    "Lifestyle Candid (Human element)",
    "Phone Screen Context (Mockup)",
    "Aesthetic Blur / Bokeh",
    "Motion Blur (Dynamic)",
    "Mirror Selfie / Reflection",
    "Behind The Scenes (Messy aesthetic)"
]

# Kategori 3: PRINT MEDIA (Layout)
ANGLES_PRINT = [
    "Rule of Thirds (Left/Right)",
    "Bottom Composition (Header Space)",
    "Wide Panoramic",
    "Minimalist Studio",
    "Corner Composition",
    "Selective Focus (Blurry foreground)",
    "Top Down Center Space"
]

def get_angles(category, qty):
    if category == "Object Slice (PNG Assets)": base = ANGLES_SLICE
    elif category == "Social Media (IG/TikTok)": base = ANGLES_SOCIAL
    else: base = ANGLES_PRINT
    if qty > len(base): return random.sample(base * 2, qty)
    return random.sample(base, qty)

# ==========================================
# 4. SIDEBAR SETUP
# ==========================================
st.sidebar.header("⚡ Engine Setup")

if 'app_keys' not in st.session_state:
    st.session_state.app_keys = []

raw_input = st.sidebar.text_area("API Keys:", height=100, placeholder="AIzaSy...")

if raw_input:
    keys = clean_keys(raw_input)
    if keys:
        st.session_state.app_keys = keys
        st.sidebar.success(f"✅ {len(keys)} Key Ready")
    else:
        st.sidebar.error("❌ Key Invalid")

st.sidebar.markdown("---")
st.sidebar.subheader("🤖 Pilih Platform AI")
ai_platform = st.sidebar.radio(
    "Target Generator:",
    ["Midjourney v6", "Flux.1", "Ideogram 2.0"],
    captions=[
        "Standard Gold. Artistik & Parameter.", 
        "Spesialis Fotorealistik & Presisi.", 
        "Juara Tipografi & Grafis."
    ]
)

# ==========================================
# 5. UI UTAMA
# ==========================================
st.title(f"⚡ Microstock Gen: {ai_platform} Mode")
st.caption("Fokus: Realisme, Tekstur Alami, dan Kepatuhan Adobe Stock.")

col1, col2 = st.columns(2)

with col1:
    topic = st.text_input("💡 Topik / Objek", placeholder="Contoh: Fresh Croissant / Business Woman")
    category = st.radio("🎯 Target Output:", ["Object Slice (PNG Assets)", "Social Media (IG/TikTok)", "Print Media (Flyer)"])

with col2:
    # Logic Aspect Ratio berdasarkan Platform
    if ai_platform == "Midjourney v6":
        # MJ pakai parameter --ar
        if category == "Object Slice (PNG Assets)":
            ar_display = "--ar 1:1"
        elif category == "Social Media (IG/TikTok)":
            ar_display = st.selectbox("📐 Rasio", ["--ar 9:16", "--ar 4:5"])
        else:
            ar_display = st.selectbox("📐 Rasio", ["--ar 2:3", "--ar 3:2", "--ar 4:3"])
        ar_prompt_instruction = f"Add parameter {ar_display} at the end."
        
    else:
        # Flux dan Ideogram biasanya handle AR di UI, bukan di prompt.
        # Tapi kita masukkan deskripsi komposisi di prompt untuk memperkuat.
        if category == "Object Slice (PNG Assets)":
            ar_display = "Square (1:1)"
            ar_prompt_instruction = "Describe a square composition."
        elif category == "Social Media (IG/TikTok)":
            ar_display = "Vertical (9:16)"
            ar_prompt_instruction = "Explicitly describe a vertical, tall composition."
        else:
            ar_display = "Standard Print Ratio"
            ar_prompt_instruction = "Describe a balanced print layout composition."
            
        st.info(f"ℹ️ Untuk {ai_platform}, atur rasio **{ar_display}** pada setting aplikasi generate Anda.")

    qty = st.slider("🔢 Jumlah Variasi (Max 10)", 1, 10, 5)

# ==========================================
# 6. GENERATOR ENGINE
# ==========================================
if st.button(f"🚀 Generate Prompts untuk {ai_platform}", type="primary"):
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
            status.text(f"⏳ Meracik Konsep {i+1}...")
            
            success = False
            attempts = 0
            
            while not success and attempts < len(keys):
                current_key = keys[key_idx]
                
                try:
                    genai.configure(api_key=current_key, transport='rest')
                    model = genai.GenerativeModel(model_name)
                    
                    # === LOGIKA PROMPTING BERDASARKAN PLATFORM ===
                    
                    if ai_platform == "Midjourney v6":
                        # Gaya MJ: Comma separated tags, teknis, parameter di ujung
                        sys_prompt = f"""
                        Role: Midjourney Expert v6.
                        Task: Create 1 prompt for {category}. Subject: {topic}. Angle: {angle}.
                        
                        RULES:
                        1. Style: Raw photography, stock photo style.
                        2. Format: Subject description, environment, lighting, technical specs, parameters.
                        3. CRITICAL: Use keywords 'shot on Canon R5', 'natural texture', 'film grain'.
                        4. {ar_prompt_instruction}
                        5. APPEND: --style raw --stylize 50
                        OUTPUT: Raw prompt text only.
                        """
                        
                    elif ai_platform == "Flux.1":
                        # Gaya Flux: Natural Language, Deskriptif, Detail Tekstur
                        sys_prompt = f"""
                        Role: Professional Photographer (Flux.1 Expert).
                        Task: Write a detailed caption for a photo. Category: {category}. Subject: {topic}. Angle: {angle}.
                        
                        RULES:
                        1. Style: Hyper-realistic, unpolished, amateur photography feel.
                        2. Format: Use natural sentences (NOT comma separated tags). Describe the light hitting the surface, the skin pores, the dust, the imperfections.
                        3. CRITICAL: {ar_prompt_instruction} Do NOT use '--ar' or parameters. Just describe the visual.
                        4. Focus on material authenticity.
                        OUTPUT: Raw description text only.
                        """
                        
                    elif ai_platform == "Ideogram 2.0":
                        # Gaya Ideogram: Komposisi Kuat, Grafis, Jelas
                        sys_prompt = f"""
                        Role: Art Director (Ideogram Expert).
                        Task: Create 1 image description. Category: {category}. Subject: {topic}. Angle: {angle}.
                        
                        RULES:
                        1. Style: Clean, strong composition, stock photography.
                        2. Focus on Visual Hierarchy and Layout.
                        3. If 'Print Media', describe exactly where the empty space is.
                        4. If 'Object Slice', describe the white background isolation clearly.
                        5. {ar_prompt_instruction} No parameters.
                        OUTPUT: Raw description text only.
                        """

                    response = model.generate_content(sys_prompt, safety_settings=SAFETY)
                    
                    if response.text:
                        clean_p = response.text.strip().replace('"', '').replace("`", "").replace("Prompt:", "")
                        
                        # Post-Processing khusus MJ (Double check parameter)
                        if ai_platform == "Midjourney v6" and "--style raw" not in clean_p:
                            clean_p += " --style raw"
                            
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
            st.success(f"✅ Selesai! {len(results)} Prompt untuk {ai_platform}.")
            
            # Download
            txt_out = f"PLATFORM: {ai_platform}\nTOPIK: {topic}\n\n"
            for idx, r in enumerate(results):
                txt_out += f"[{r[0]}]\n{r[1]}\n\n"
            
            st.download_button("📥 Download .txt", txt_out, f"prompts_{ai_platform}_{topic}.txt")
            
            st.markdown("---")
            for idx, (ang, txt) in enumerate(results):
                st.markdown(f"**#{idx+1} {ang}**")
                st.code(txt, language="text")
        else:
            st.error("❌ Gagal. Cek Key.")
