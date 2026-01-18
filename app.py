import streamlit as st
import time
import random
import sys

# ==========================================
# 1. SETUP & LIBRARY CHECK
# ==========================================
st.set_page_config(page_title="Microstock Engine Final", page_icon="💎", layout="wide")

try:
    import google.generativeai as genai
    from google.generativeai.types import HarmCategory, HarmBlockThreshold
except ImportError:
    st.error("❌ Library Error. Pastikan requirements.txt berisi: google-generativeai>=0.8.3")
    st.stop()

# ==========================================
# 2. FUNGSI-FUNGSI KRUSIAL (THE FIXES)
# ==========================================

# A. PEMBERSIH KEY (Anti-Spasi/Kutip)
def clean_keys(raw_text):
    if not raw_text: return []
    # Ubah enter jadi koma, pisahkan, bersihkan kutip & spasi
    candidates = raw_text.replace('\n', ',').split(',')
    cleaned = []
    for c in candidates:
        k = c.strip().replace('"', '').replace("'", "")
        if k.startswith("AIza") and len(k) > 20:
            cleaned.append(k)
    return list(set(cleaned))

# B. AUTO-DETECT MODEL (Anti-404) -> INI YANG SEMPAT SAYA HILANGKAN
# Fungsi ini mencari model yang BENAR-BENAR ADA di akun Anda
@st.cache_resource
def get_best_model(_api_key):
    try:
        # PENTING: transport='rest' agar tembus firewall Streamlit
        genai.configure(api_key=_api_key, transport='rest')
        
        # Minta daftar model ke Google
        models = list(genai.list_models())
        available = [m.name for m in models if 'generateContent' in m.supported_generation_methods]
        
        # Prioritas: Flash -> Pro -> Apapun
        for m in available:
            if 'flash' in m and '1.5' in m: return m
        for m in available:
            if 'pro' in m and '1.5' in m: return m
        for m in available:
            if 'pro' in m: return m
            
        return available[0] if available else "models/gemini-1.5-flash"
    except Exception as e:
        # Jika gagal detect, return default aman
        return "models/gemini-1.5-flash"

# C. SAFETY SETTINGS (Anti-Blokir "Unsafe")
SAFETY_SETTINGS = {
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
}

# D. ANGLE VARIATION (Agar hasil tidak monoton)
STOCK_ANGLES = [
    "Business Concept (Corporate, office, planning)",
    "Modern Technology (Gadget, screen, futuristic)",
    "Culinary & Food (Ingredients, dining, close-up)",
    "Lifestyle (Authentic, family, candid)",
    "Abstract Background (Texture, bokeh, pattern)",
    "Education (School, books, learning)",
    "Health & Wellness (Yoga, medical, organic)",
    "Interior Design (Cozy, furniture, window)",
    "Travel & Outdoor (Landscape, adventure, nature)",
    "Creative Art (Surreal, paint, artistic)"
]

def get_random_angles(qty):
    if qty > len(STOCK_ANGLES):
        base = STOCK_ANGLES * (qty // len(STOCK_ANGLES) + 1)
        return random.sample(base, qty)
    return random.sample(STOCK_ANGLES, qty)

# ==========================================
# 3. SIDEBAR & INPUT
# ==========================================
st.sidebar.header("💎 Configuration")
st.sidebar.info("Paste semua API Key Anda di bawah ini.")

# Session state untuk menyimpan key
if 'final_keys' not in st.session_state:
    st.session_state.final_keys = []

raw_input = st.sidebar.text_area("API Keys:", height=150, placeholder="AIzaSy...")

if raw_input:
    keys = clean_keys(raw_input)
    if keys:
        st.session_state.final_keys = keys
        st.sidebar.success(f"✅ {len(keys)} Key Valid")
        
        # Deteksi model sekali saja di awal
        detected_model = get_best_model(keys[0])
        st.sidebar.caption(f"🧠 Engine: `{detected_model}`")
    else:
        st.sidebar.error("❌ Format Key Salah")

# ==========================================
# 4. UI UTAMA
# ==========================================
VISUAL_MODES = {
    "photo": {"label": "📸 Photorealistic", "prompt": "photorealistic, 8k, highly detailed, canon r5, commercial photography, depth of field"},
    "3d": {"label": "🧊 3D Render", "prompt": "3d render, cinema 4d, isometric, cute style, soft lighting, clay material, --ar 1:1"},
    "vector": {"label": "🎨 Flat Vector", "prompt": "flat vector illustration, white background, simple shapes, sticker style, thick outline, --ar 1:1"},
    "minimal": {"label": "⚪ Minimalist", "prompt": "minimalist photography, vast negative space, soft pastel colors, clean composition, --ar 16:9"}
}

st.title("💎 Microstock Engine (Final Fix)")
st.caption("Auto-Model Detection + REST Protocol + Concept Randomizer")

col1, col2 = st.columns(2)
with col1:
    topic = st.text_input("💡 Topik", "Ramadhan")
    trend = st.text_input("📈 Trend (Opsional)", "Modern Islamic, Gold & White")
with col2:
    mode_key = st.selectbox("🎨 Gaya Visual", list(VISUAL_MODES.keys()), format_func=lambda x: VISUAL_MODES[x]['label'])
    qty = st.slider("🔢 Jumlah Variasi", 1, 20, 5)

# ==========================================
# 5. GENERATOR CORE
# ==========================================
if st.button("🚀 Generate Prompts", type="primary"):
    keys = st.session_state.final_keys
    
    if not keys:
        st.error("⚠️ Masukkan Key di Sidebar dulu!")
    elif not topic:
        st.warning("⚠️ Masukkan Topik!")
    else:
        # Siapkan Variabel
        results = []
        pbar = st.progress(0)
        status = st.empty()
        
        # Ambil Model Terbaik (Pakai key pertama buat deteksi)
        active_model_name = get_best_model(keys[0])
        
        # Ambil variasi angle
        angles = get_random_angles(qty)
        mode_prompt = VISUAL_MODES[mode_key]['prompt']
        
        key_idx = 0
        
        for i in range(qty):
            angle = angles[i]
            status.text(f"⏳ Meracik Konsep {i+1}: {angle.split('(')[0]}...")
            
            success = False
            attempts = 0
            
            # Retry Logic
            while not success and attempts < len(keys):
                current_key = keys[key_idx]
                
                try:
                    # 1. KONFIGURASI (REST WAJIB ADA)
                    genai.configure(api_key=current_key, transport='rest')
                    model = genai.GenerativeModel(active_model_name)
                    
                    # 2. PROMPT
                    full_prompt = f"""
                    Role: Stock Photographer.
                    Subject: {topic}.
                    Concept Angle: {angle}.
                    Visual Style: {mode_prompt} {trend}.
                    
                    Instruction: Create a detailed image description based on the Concept Angle. 
                    Avoid generic descriptions. Output raw text only.
                    """
                    
                    # 3. GENERATE (Safety OFF)
                    response = model.generate_content(full_prompt, safety_settings=SAFETY_SETTINGS)
                    
                    # 4. AMBIL HASIL AMAN
                    if response.text:
                        clean_text = response.text.strip().replace('"','').replace("`","").replace("Prompt:", "")
                        results.append((angle.split('(')[0], clean_text))
                        success = True
                        
                except Exception as e:
                    # Silent Failover (Ganti key diam-diam kalau gagal)
                    pass
                
                # Rotasi Key
                key_idx = (key_idx + 1) % len(keys)
                
                if success:
                    time.sleep(0.5) # Jeda sedikit
                    break
                else:
                    attempts += 1
                    time.sleep(1)
            
            if not success:
                st.warning(f"⚠️ Gagal generate prompt ke-{i+1} (Server sibuk).")
                
            pbar.progress((i+1)/qty)
            
        status.empty()
        
        # TAMPILKAN HASIL
        if results:
            st.success(f"✅ Selesai! {len(results)} Prompt Berhasil.")
            st.markdown("---")
            
            # Download
            txt_out = "\n\n".join([f"[{r[0]}] {r[1]}" for r in results])
            st.download_button("📥 Download .txt", txt_out, "prompts.txt")
            
            # Display
            for idx, (ang, txt) in enumerate(results):
                st.markdown(f"**#{idx+1} Konsep: {ang}**")
                st.code(txt, language="text")
        else:
            st.error("❌ Gagal total. Kemungkinan semua Key limit atau koneksi bermasalah.")
