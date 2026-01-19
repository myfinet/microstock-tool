import streamlit as st
import google.generativeai as genai
import time
import random

# ==========================================
# 1. SETUP & CONFIG
# ==========================================
st.set_page_config(
    page_title="Microstock Prompt (Adobe Mode)",
    page_icon="🛡️",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .stCodeBlock {margin-bottom: 0px;}
    div[data-testid="stExpander"] {border: 1px solid #ddd; border-radius: 5px;}
</style>
""", unsafe_allow_html=True)

# Cek Library
try:
    import google.generativeai as genai
    from google.generativeai.types import HarmCategory, HarmBlockThreshold
except ImportError:
    st.error("❌ Library Error. Update requirements.txt: google-generativeai>=0.8.3")
    st.stop()

# ==========================================
# 2. CORE LOGIC (THE FIXES)
# ==========================================

# A. Pembersih Key
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
        genai.configure(api_key=_api_key, transport='rest') # REST Protocol Wajib
        models = list(genai.list_models())
        available = [m.name for m in models if 'generateContent' in m.supported_generation_methods]
        
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
# 3. LOGIKA "ADOBE DIVERSIFICATION"
# ==========================================
# Ini adalah "Otak" untuk mencegah gambar mirip (Visual Spam)
# Kita paksa AI menggunakan lensa berbeda untuk setiap gambar.

DIVERSE_ANGLES = [
    "Macro / Close-up Detail (Focus on texture/material)",
    "Wide Angle / Environment (Focus on context/location)",
    "Human Interaction / Hands (Action shot, using the object)",
    "Flat Lay / Knolling (Organized from top-down)",
    "Low Angle / Hero Shot (Looking up, majestic)",
    "Isometric / 3D Icon Style (Clean geometry)",
    "Candid Lifestyle (Natural, not posed, authentic)",
    "Abstract / Background Usage (Blur, bokeh, pattern)"
]

def get_unique_angles(qty):
    # Ambil angle unik sejumlah qty, acak urutannya
    if qty > len(DIVERSE_ANGLES):
        base = DIVERSE_ANGLES * 2
        return random.sample(base, qty)
    return random.sample(DIVERSE_ANGLES, qty)

# ==========================================
# 4. SIDEBAR INPUT
# ==========================================
st.sidebar.header("🛡️ Adobe Compliance")
st.sidebar.info("Mode ini memaksa variasi konsep agar tidak ditolak karena 'Similar Content'.")

# Session State untuk Key
if 'prompt_keys' not in st.session_state:
    st.session_state.prompt_keys = []

raw_input = st.sidebar.text_area("API Keys:", height=150, placeholder="AIzaSy...")

if raw_input:
    keys = clean_keys(raw_input)
    if keys:
        st.session_state.prompt_keys = keys
        st.sidebar.success(f"✅ {len(keys)} Key Ready")
        mod = get_best_model(keys[0])
        st.sidebar.caption(f"Engine: {mod}")
    else:
        st.sidebar.error("❌ Key Invalid")

# ==========================================
# 5. UI UTAMA
# ==========================================
st.title("🛡️ Microstock Prompt (Strict Mode)")
st.caption("Fokus: Visual Diversification & Commercial Viability.")

col1, col2 = st.columns(2)

with col1:
    topic = st.text_input("💡 Topik Utama", placeholder="Contoh: Barista Coffee")
    style_trend = st.text_input("📈 Style/Trend", placeholder="Contoh: Cinematic Lighting, Warm Tone")

with col2:
    # Mode Aspect Ratio
    ar_mode = st.selectbox("📐 Aspect Ratio", ["--ar 16:9 (Landscape)", "--ar 4:5 (Vertical)", "--ar 1:1 (Square)"])
    # STRICT LIMIT: Maksimal 10 sesuai permintaan
    qty = st.slider("🔢 Jumlah Konsep (Max 10)", 1, 10, 5)

# ==========================================
# 6. GENERATOR ENGINE
# ==========================================
if st.button("🚀 Generate Distinct Concepts", type="primary"):
    keys = st.session_state.prompt_keys
    
    if not keys:
        st.error("⚠️ Masukkan API Key di Sidebar!")
    elif not topic:
        st.warning("⚠️ Masukkan Topik!")
    else:
        results = []
        pbar = st.progress(0)
        status = st.empty()
        
        # Ambil Angle Unik
        angles = get_unique_angles(qty)
        
        # Setup Loop
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
                    
                    # SYSTEM PROMPT (Strict Adobe Guidelines)
                    sys_prompt = f"""
                    Role: Professional Microstock Prompter.
                    Task: Create 1 DISTINCT commercial image prompt.
                    
                    INPUTS:
                    - Subject: {topic}
                    - Mandatory Angle/Lens: {angle}
                    - Style: {style_trend}
                    - AR: {ar_mode}
                    
                    RULES:
                    1. DIVERSIFICATION: Do NOT describe the generic subject. Focus entirely on the specific ANGLE provided.
                    2. QUALITY: Use keywords: 8k, sharp focus, commercial photography, high quality.
                    3. OUTPUT: Raw prompt text only. No intro.
                    """
                    
                    response = model.generate_content(sys_prompt, safety_settings=SAFETY)
                    
                    if response.text:
                        clean_p = response.text.strip().replace('"', '').replace("`", "").replace("Prompt:", "")
                        # Simpan Angle & Prompt
                        results.append((angle.split('(')[0], clean_p))
                        success = True
                        
                except Exception:
                    pass # Silent failover
                
                # Rotasi Key
                key_idx = (key_idx + 1) % len(keys)
                
                if success:
                    time.sleep(0.5)
                    break
                else:
                    attempts += 1
                    time.sleep(1)
            
            pbar.progress((i+1)/qty)
        
        status.empty()
        
        # TAMPILKAN HASIL
        if results:
            st.success(f"✅ Selesai! {len(results)} Konsep Unik Terbuat.")
            
            # Download TXT (Format Rapi)
            txt_out = ""
            for idx, r in enumerate(results):
                txt_out += f"Concept {idx+1} ({r[0]}):\n{r[1]}\n\n"
                
            st.download_button("📥 Download Semua (.txt)", txt_out, f"prompts_{topic}.txt")
            
            st.markdown("---")
            
            # Tampilan 1 Blok 1 Prompt + Tombol Copy
            for idx, (ang, txt) in enumerate(results):
                st.markdown(f"**Concept #{idx+1}: {ang}**")
                st.code(txt, language="text")
                
        else:
            st.error("❌ Gagal. Cek API Key atau Koneksi.")
