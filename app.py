import streamlit as st
import time
import random
import json
import os
from datetime import datetime
from PIL import Image

# ==========================================
# 1. SETUP & LIBRARY
# ==========================================
st.set_page_config(
    page_title="Microstock Gen v5.2",
    page_icon="⚡",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .stCodeBlock {margin-bottom: 0px;}
    div[data-testid="stExpander"] {border: 1px solid #e0e0e0; border-radius: 8px;}
    .char-count {font-size: 12px; color: #666; margin-top: 5px; font-family: monospace;}
    .translated-text {font-size: 14px; font-weight: bold; color: #2e7bcf; background-color: #f0f8ff; padding: 8px; border-radius: 5px; border: 1px solid #cce5ff; margin-bottom: 15px;}
</style>
""", unsafe_allow_html=True)

try:
    import google.generativeai as genai
    from google.generativeai.types import HarmCategory, HarmBlockThreshold
except ImportError:
    st.error("❌ Library Error. Requirements: google-generativeai>=0.8.3")
    st.stop()

# ==========================================
# 2. SIMPLE CACHE SYSTEM (Auto-Save)
# ==========================================
CACHE_FILE = "api_cache.json"

def load_cache():
    """Mengambil key terakhir dari file"""
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r') as f:
                data = json.load(f)
                return data.get("keys", ""), data.get("timestamp", "")
        except:
            return "", ""
    return "", ""

def save_cache(keys_text):
    """Menyimpan key ke file saat validasi sukses"""
    data = {
        "keys": keys_text,
        "timestamp": datetime.now().strftime("%d %B %Y, %H:%M")
    }
    with open(CACHE_FILE, 'w') as f:
        json.dump(data, f)

# ==========================================
# 3. UTILITIES
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
    try:
        genai.configure(api_key=api_key, transport='rest')
        models = list(genai.list_models())
        found_model = None
        candidates = [m.name for m in models if 'generateContent' in m.supported_generation_methods]
        
        # Prioritas Model (Multimodal Friendly)
        for m in candidates:
            if 'flash' in m and '1.5' in m: found_model = m; break
        if not found_model:
            for m in candidates:
                if 'pro' in m and '1.5' in m: found_model = m; break
        if not found_model and candidates: found_model = candidates[0]
            
        if not found_model: return False, "No Model", None

        model = genai.GenerativeModel(found_model)
        model.generate_content("Hi", generation_config={'max_output_tokens': 1})
        return True, "Active", found_model
    except Exception as e:
        err = str(e)
        if "429" in err: return False, "Limit", None
        return False, "Error", None

def translate_topic(text, api_key, model_name):
    if not text: return ""
    try:
        genai.configure(api_key=api_key, transport='rest')
        model = genai.GenerativeModel(model_name)
        sys_prompt = f"""Translate to English for Image Prompt. Input: "{text}". Output (English Only):"""
        response = model.generate_content(sys_prompt)
        return response.text.strip()
    except:
        return text

# ==========================================
# 4. SIDEBAR (SIMPEL & CUKUP 1 BLOK)
# ==========================================
st.sidebar.title("🔑 API Key")

# Load data lama
cached_keys, last_time = load_cache()

# Text Area dengan nilai default dari cache
raw_input = st.sidebar.text_area("Paste API Keys:", value=cached_keys, height=100, placeholder="AIzaSy...")

# Tampilkan Timestamp di bawah kotak
if last_time:
    st.sidebar.caption(f"🕒 Terakhir dipakai: {last_time}")

# Session State untuk menyimpan data validasi aktif
if 'active_keys_data' not in st.session_state:
    st.session_state.active_keys_data = []

if st.sidebar.button("Validasi Key", type="primary"):
    candidates = clean_keys(raw_input)
    if not candidates:
        st.sidebar.error("❌ Key kosong.")
    else:
        valid_data = []
        progress = st.sidebar.progress(0)
        status = st.sidebar.empty()
        
        for i, key in enumerate(candidates):
            status.text(f"Cek {i+1}...")
            is_alive, msg, model_name = check_key_health(key)
            if is_alive:
                valid_data.append({'key': key, 'model': model_name})
            progress.progress((i + 1) / len(candidates))
            
        st.session_state.active_keys_data = valid_data
        status.empty()
        progress.empty()
        
        if valid_data:
            st.sidebar.success(f"✅ {len(valid_data)} Key Aktif")
            # Simpan ke cache agar besok tidak perlu paste lagi
            save_cache(raw_input)
            # Refresh halaman agar timestamp update (opsional, tapi bagus utk UX)
            time.sleep(0.5)
            st.rerun()
        else:
            st.sidebar.error("💀 Semua Key Mati.")

# Indikator status sederhana
if st.session_state.active_keys_data:
    st.sidebar.info("🟢 Ready")
else:
    # Jika belum divalidasi tapi ada cache, coba validasi otomatis (Lazy Load)
    if cached_keys and not st.session_state.active_keys_data:
        st.sidebar.warning("⚠️ Klik Validasi untuk mengaktifkan.")

# ==========================================
# 5. LOGIKA GENERATOR (CORE)
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
# 6. UI UTAMA
# ==========================================
st.title("⚡ Microstock Gen v5.2")
st.caption("Simple Cache • Vision • Auto-Translate")

ai_platform = st.radio("🤖 Platform:", ["Midjourney v6", "Flux.1", "Ideogram 2.0"], horizontal=True)

col1, col2 = st.columns([1.2, 1])

with col1:
    topic = st.text_input("💡 Topik (Auto-Translate)", placeholder="Contoh: Kucing oren makan ikan")
    st.markdown("---")
    uploaded_file = st.file_uploader("🖼️ Upload Referensi (Opsional)", type=["jpg", "png", "webp"])
    
    img_ref_mode = None
    pil_image = None
    
    if uploaded_file:
        st.image(uploaded_file, width=200)
        pil_image = Image.open(uploaded_file)
        img_ref_mode = st.radio("🎯 Mode Referensi:", ["🎨 Style Ref", "📦 Object Ref", "🔄 Variation"])

with col2:
    category = st.radio("🎯 Kategori:", ["Object Slice (PNG Assets)", "Social Media (IG/TikTok)", "Print Media (Flyer/Banner)"])
    
    if ai_platform == "Midjourney v6":
        if category == "Object Slice (PNG Assets)": ar_display = "--ar 1:1"
        elif category == "Social Media (IG/TikTok)": ar_display = st.selectbox("📐 Rasio", ["--ar 9:16", "--ar 4:5"])
        else: ar_display = st.selectbox("📐 Rasio", ["--ar 16:9", "--ar 2:3", "--ar 3:2", "--ar 4:3"])
        ar_instr = f"Add {ar_display.split(' ')[0] + ' ' + ar_display.split(' ')[1]} at end."
        limit_msg = "Safe Limit: ~1800 chars"
    else:
        st.info(f"ℹ️ {ai_platform}: Atur rasio manual.")
        ar_instr = "Describe composition explicitly."
        limit_msg = "Hard Limit: 2000 chars"
        
    qty = st.slider("🔢 Jumlah Variasi", 1, 10, 5)
    st.caption(f"🛡️ {limit_msg}")

st.markdown("---")

# ==========================================
# 7. EKSEKUSI
# ==========================================
if st.button(f"🚀 Generate ({ai_platform})", type="primary"):
    
    keys_data = st.session_state.active_keys_data
    
    if not keys_data:
        st.error("⛔ Klik tombol 'Validasi Key' di Sidebar dulu!")
        st.stop()
        
    if not uploaded_file and not topic:
        st.warning("⚠️ Masukkan Topik atau Upload Gambar.")
        st.stop()
        
    # Translate
    english_topic = ""
    if topic:
        with st.spinner("🌍 Menerjemahkan..."):
            english_topic = translate_topic(topic, keys_data[0]['key'], keys_data[0]['model'])
            st.markdown(f"<div class='translated-text'>🇺🇸 EN: {english_topic}</div>", unsafe_allow_html=True)

    results = []
    st.sidebar.markdown("---")
    error_log = st.sidebar.expander("📜 Log Error", expanded=False)
    
    pbar = st.progress(0)
    angles = get_angles(category, qty)
    key_idx = 0
    
    for i in range(qty):
        angle = angles[i]
        success = False
        attempts = 0
        
        while not success and attempts < len(keys_data):
            current_data = keys_data[key_idx]
            try:
                genai.configure(api_key=current_data['key'], transport='rest')
                model = genai.GenerativeModel(current_data['model'])
                
                limit_instr = "Output < 1800 chars. Concise."
                
                base_prompt = f"""
                Role: {ai_platform.split(' ')[0]} Expert.
                Task: Detailed image prompt.
                Category: {category}. Angle: {angle}.
                RULES: Commercial quality. {ar_instr} {limit_instr}
                OUTPUT: Raw prompt text only.
                """
                
                if uploaded_file and pil_image:
                    if img_ref_mode.startswith("🎨 Style"):
                        vision_instr = f"Analyze STYLE (lighting/color). Apply to: '{english_topic}'."
                    elif img_ref_mode.startswith("📦 Object"):
                        vision_instr = f"Identify MAIN OBJECT. Place in new context: '{english_topic}'. Angle: {angle}."
                    else:
                        vision_instr = f"Create creative VARIATION. Angle: {angle}. Context: '{english_topic}'."
                    final_input = [base_prompt + vision_instr, pil_image]
                else:
                    text_instr = f"Subject: '{english_topic}'. Angle: {angle}."
                    final_input = base_prompt + text_instr

                response = model.generate_content(final_input, safety_settings=SAFETY)
                
                if response.text:
                    clean_p = response.text.strip().replace('"', '').replace("`", "").replace("Prompt:", "")
                    if ai_platform == "Midjourney v6" and "--style raw" not in clean_p:
                        clean_p += " --style raw"
                    if len(clean_p) > 2000: clean_p = clean_p[:1997] + "..."
                    results.append((angle, clean_p))
                    success = True
            
            except Exception as e:
                error_log.warning(f"Key #{key_idx+1}: {str(e)}")
                pass
            
            key_idx = (key_idx + 1) % len(keys_data)
            if success: break
            else: attempts += 1
            time.sleep(0.5)
        
        pbar.progress((i+1)/qty)
    
    if results:
        st.success(f"✅ Selesai! {len(results)} Prompt.")
        
        ref_txt = f"IMAGE REF: {img_ref_mode}" if uploaded_file else ""
        txt_out = f"PLATFORM: {ai_platform}\nTOPIK: {topic} ({english_topic})\n{ref_txt}\n\n"
        for idx, r in enumerate(results):
            txt_out += f"[{r[0]}]\n{r[1]}\n\n"
        
        st.download_button("📥 Download .txt", txt_out, f"prompts_v5.txt")
        
        for idx, (ang, txt) in enumerate(results):
            st.markdown(f"**#{idx+1} {ang}**")
            st.code(txt, language="text")
            st.caption(f"Len: {len(txt)} chars")
    else:
        st.error("❌ Gagal. Cek Log.")
