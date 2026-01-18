import streamlit as st
import google.generativeai as genai
import time
import random
from google.generativeai.types import HarmCategory, HarmBlockThreshold, GenerationConfig

# ==========================================
# 1. KONFIGURASI HALAMAN
# ==========================================
st.set_page_config(
    page_title="Microstock Brain V2",
    page_icon="🧠",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .stCodeBlock {margin-bottom: 0px;}
    div[data-testid="stExpander"] {border: 1px solid #333;}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. LOGIKA UTAMA & RANDOMIZER
# ==========================================

# --- DAFTAR ANGLE/NICHE MICROSTOCK (RAHASIA VARIASI) ---
# Ini adalah daftar "kacamata" yang akan dipakai AI agar tidak monoton.
STOCK_ANGLES = [
    "Business & Corporate Concept (Office setting, shaking hands, planning)",
    "Modern Technology & Gadget (Smartphone app, screen, futuristic)",
    "Culinary & Food Photography (Ingredients, cooking process, dining)",
    "Lifestyle & Authentic People (Candid moments, emotions, family)",
    "Abstract & Background (Texture, bokeh, geometric patterns, blur)",
    "Education & Learning (Books, studying, classroom, writing)",
    "Health & Wellness (Yoga, meditation, healthy food, medical)",
    "Interior & Home Decor (Cozy room, furniture, window view)",
    "Travel & Adventure (Landscape, backpack, map, outdoor)",
    "Creative & Artsy (Paint, surreal composition, double exposure)"
]

def get_random_angles(qty):
    """Mengambil daftar angle unik sebanyak jumlah request"""
    # Jika request lebih banyak dari daftar, kita putar ulang tapi acak
    if qty > len(STOCK_ANGLES):
        base = STOCK_ANGLES * (qty // len(STOCK_ANGLES) + 1)
        return random.sample(base, qty)
    return random.sample(STOCK_ANGLES, qty)

def clean_api_keys(raw_text):
    if not raw_text: return []
    candidates = raw_text.replace('\n', ',').split(',')
    cleaned = []
    for c in candidates:
        k = c.strip().replace('"', '').replace("'", "")
        if k.startswith("AIza") and len(k) > 30:
            cleaned.append(k)
    return list(set(cleaned))

@st.cache_resource
def get_best_model(_api_key):
    try:
        genai.configure(api_key=_api_key, transport='rest')
        models = list(genai.list_models())
        available = [m.name for m in models if 'generateContent' in m.supported_generation_methods]
        
        # Prioritas Model
        for m in available:
            if 'flash' in m and '1.5' in m: return m
        for m in available:
            if 'pro' in m: return m
        return available[0] if available else "models/gemini-1.5-flash"
    except:
        return "models/gemini-1.5-flash"

# Konfigurasi agar AI lebih liar/kreatif (Temperature Tinggi)
CREATIVE_CONFIG = GenerationConfig(
    temperature=0.85, # 0.0 kaku, 1.0 sangat acak. 0.85 sweet spot untuk ide kreatif.
    top_p=0.95,
    top_k=40,
    max_output_tokens=200,
)

SAFETY_SETTINGS = {
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
}

# ==========================================
# 3. SIDEBAR
# ==========================================
st.sidebar.header("🧠 Brain V2 Setup")

if 'api_keys' not in st.session_state:
    st.session_state.api_keys = []

raw_input = st.sidebar.text_area("Paste API Keys:", height=150, placeholder="AIzaSy...")

if raw_input:
    keys = clean_api_keys(raw_input)
    if keys:
        st.session_state.api_keys = keys
        st.sidebar.success(f"✅ {len(keys)} Key Loaded")
        active_model = get_best_model(keys[0])
        st.sidebar.caption(f"Engine: `{active_model.split('/')[-1]}`")
    else:
        st.sidebar.error("❌ Key Invalid")

# ==========================================
# 4. PRESET MODE (VISUAL STYLE ONLY)
# ==========================================
# Mode ini hanya mengatur "Look" (Tampilan), bukan "Subject" (Objek).
# Subjek akan diatur oleh Randomizer Angle.
VISUAL_MODES = {
    "photorealistic": {
        "label": "📸 Photorealistic Stock",
        "params": "photorealistic, 8k, highly detailed, shot on Canon R5, 85mm lens, depth of field, commercial lighting"
    },
    "3d_render": {
        "label": "🧊 3D Render / C4D",
        "params": "3d render, cinema 4d, octane render, clay material, soft lighting, isometric, cute style, --ar 1:1"
    },
    "vector": {
        "label": "🎨 Flat Vector",
        "params": "flat vector illustration, white background, simple shapes, adobe illustrator, sticker style, no shadow, --ar 1:1"
    },
    "minimalist": {
        "label": "⚪ Minimalist / Copy Space",
        "params": "minimalist photography, vast negative space, clean composition, soft pastel colors, --ar 16:9"
    }
}

# ==========================================
# 5. UI UTAMA
# ==========================================
st.title("🧠 Microstock Brain V2 (Anti-Repetisi)")
st.info("Fitur Baru: Setiap prompt sekarang otomatis disuntikkan 'Angle Microstock' acak (Bisnis, Tech, Lifestyle, dll) agar objek tidak berulang.")

col1, col2 = st.columns([1, 1])

with col1:
    topic = st.text_input("💡 Topik Utama", placeholder="Contoh: Ramadhan")
    # Trend dijadikan opsional tapi berpengaruh
    trend = st.text_input("📈 Color/Mood Trend", placeholder="Contoh: Gold & White, Cyberpunk, Warm Tone")

with col2:
    selected_mode = st.selectbox("🎨 Visual Style", list(VISUAL_MODES.keys()), format_func=lambda x: VISUAL_MODES[x]['label'])
    qty = st.slider("🔢 Jumlah Variasi", 1, 15, 5)

# ==========================================
# 6. GENERATOR ENGINE
# ==========================================
if st.button("🚀 Generate Beragam Ide", type="primary", use_container_width=True):
    if not st.session_state.api_keys:
        st.error("⚠️ Masukkan API Key dulu!")
    elif not topic:
        st.warning("⚠️ Isi topiknya dulu.")
    else:
        mode_params = VISUAL_MODES[selected_mode]['params']
        keys = st.session_state.api_keys
        results = []
        angles_list = get_random_angles(qty) # Ambil daftar angle unik
        
        progress_bar = st.progress(0)
        status = st.empty()
        
        key_idx = 0
        model_name = get_best_model(keys[0])
        
        for i in range(qty):
            # Ambil angle unik untuk iterasi ini
            current_angle = angles_list[i]
            
            status.markdown(f"**Prompt {i+1}:** Mencoba angle *{current_angle.split('(')[0]}*...")
            
            success = False
            attempts = 0
            
            while not success and attempts < len(keys):
                current_key = keys[key_idx]
                try:
                    genai.configure(api_key=current_key, transport='rest')
                    model = genai.GenerativeModel(model_name)
                    
                    # SYSTEM PROMPT YANG LEBIH PINTAR & PEMAKSA
                    sys_prompt = f"""
                    You are a Creative Director for a Microstock Agency.
                    Task: Create 1 unique Midjourney prompt description.
                    
                    CORE INSTRUCTIONS:
                    1. Main Topic: "{topic}"
                    2. MANDATORY ANGLE: Interpret the topic through the lens of: **{current_angle}**.
                    3. Visual Style: {mode_params} {trend}.
                    
                    RESTRICTIONS:
                    - STOP using the generic "Mosque/Dates/Moon" combination unless the Angle specifically asks for it.
                    - IF Angle is "Technology", show apps, screens, or modern gadgets related to {topic}.
                    - IF Angle is "Business", show office settings, planning, or corporate vibes related to {topic}.
                    - IF Angle is "Food", focus on the dining table or ingredients.
                    
                    OUTPUT:
                    Return ONLY the prompt text description. No intro.
                    """
                    
                    response = model.generate_content(
                        sys_prompt, 
                        generation_config=CREATIVE_CONFIG,
                        safety_settings=SAFETY_SETTINGS
                    )
                    
                    if response.text:
                        clean_p = response.text.strip().replace('"', '').replace("'", "").replace("`", "")
                        # Tambahkan Label Angle agar user tahu ini idenya dari mana
                        results.append((current_angle.split('(')[0], clean_p))
                        success = True
                        key_idx = (key_idx + 1) % len(keys)
                        time.sleep(0.5)
                        
                except Exception:
                    key_idx = (key_idx + 1) % len(keys)
                    attempts += 1
                    time.sleep(1)
            
            progress_bar.progress((i + 1) / qty)
            
        status.empty()
        
        if results:
            st.success("✅ Selesai! Perhatikan betapa berbedanya setiap ide di bawah ini:")
            
            # Siapkan teks download (bersih tanpa label angle)
            txt_download = "\n\n".join([r[1] for r in results])
            
            st.download_button(
                "📥 Download Semua (.txt)", 
                txt_download, 
                f"variasi_{topic}.txt",
                use_container_width=True
            )
            
            st.markdown("---")
            
            for idx, (angle_name, prompt_text) in enumerate(results):
                # Tampilkan Angle sebagai Badge/Subheader
                st.markdown(f"#### #{idx+1} Konsep: {angle_name}")
                st.code(prompt_text, language="text")
