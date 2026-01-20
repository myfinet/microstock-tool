import streamlit as st
import time
import random
from PIL import Image # Library tambahan untuk proses gambar

# ==========================================
# 1. SETUP & LIBRARY
# ==========================================
st.set_page_config(
    page_title="Microstock Gen v5.0 (Vision)",
    page_icon="👁️",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .stCodeBlock {margin-bottom: 0px;}
    div[data-testid="stExpander"] {border: 1px solid #e0e0e0; border-radius: 8px;}
    .char-count {font-size: 12px; color: #666; margin-top: 5px; font-family: monospace;}
    .translated-text {font-size: 14px; font-weight: bold; color: #2e7bcf; background-color: #f0f8ff; padding: 8px; border-radius: 5px; border: 1px solid #cce5ff; margin-bottom: 15px;}
    .stImage {border-radius: 8px; border: 1px solid #ddd;}
</style>
""", unsafe_allow_html=True)

try:
    import google.generativeai as genai
    from google.generativeai.types import HarmCategory, HarmBlockThreshold
except ImportError:
    st.error("❌ Library Error. Requirements: google-generativeai>=0.8.3")
    st.stop()

# ==========================================
# 2. FUNGSI UTILITIES (VALIDASI & TRANSLATE)
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
        
        # Prioritas Model Multimodal (Flash/Pro 1.5 sangat bagus untuk gambar)
        for m in candidates:
            if 'flash' in m and '1.5' in m: found_model = m; break
        if not found_model:
            for m in candidates:
                if 'pro' in m and '1.5' in m: found_model = m; break
        if not found_model and candidates: found_model = candidates[0]
            
        if not found_model: return False, "No Model Found", None

        model = genai.GenerativeModel(found_model)
        model.generate_content("Hi", generation_config={'max_output_tokens': 1})
        return True, "Active", found_model
    except Exception as e:
        err = str(e)
        if "429" in err: return False, "Quota Limit", None
        if "400" in err: return False, "Invalid Key", None
        return False, f"Error: {err[:15]}...", None

def translate_topic(text, api_key, model_name):
    if not text: return ""
    try:
        genai.configure(api_key=api_key, transport='rest')
        model = genai.GenerativeModel(model_name)
        sys_prompt = f"""Translate to English for Image Prompt. If English, return as is. Input: "{text}". Output (English Only):"""
        response = model.generate_content(sys_prompt)
        return response.text.strip()
    except:
        return text

# ==========================================
# 3. SIDEBAR
# ==========================================
st.sidebar.title("🔑 Key Manager")

if 'active_keys_data' not in st.session_state:
    st.session_state.active_keys_data = []

raw_input = st.sidebar.text_area("Paste API Keys:", height=100, placeholder="AIzaSy...")

if st.sidebar.button("🔍 Validasi & Sync", type="primary"):
    candidates = clean_keys(raw_input)
    if not candidates:
        st.sidebar.error("❌ Key kosong.")
    else:
        valid_data = []
        progress_bar = st.sidebar.progress(0)
        status_text = st.sidebar.empty()
        
        for i, key in enumerate(candidates):
            status_text.text(f"Cek Key {i+1}...")
            is_alive, msg, model_name = check_key_health(key)
            if is_alive:
                valid_data.append({'key': key, 'model': model_name})
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
# 4. LOGIKA GENERATOR & ANGLES
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
# 5. UI GENERATOR UTAMA
# ==========================================
st.title("👁️ Microstock Gen v5.0 (Vision)")
st.caption("Multimodal: Text + Image Reference Support")

ai_platform = st.radio("🤖 Platform:", ["Midjourney v6", "Flux.1", "Ideogram 2.0"], horizontal=True)

col1, col2 = st.columns([1.2, 1]) # Kolom kiri sedikit lebih lebar untuk gambar

with col1:
    topic = st.text_input("💡 Topik (Opsional jika pakai Variasi Gambar)", placeholder="Contoh: Kucing pakai helm")
    
    # --- FITUR BARU: IMAGE UPLOADER ---
    st.markdown("---")
    uploaded_file = st.file_uploader("🖼️ Upload Referensi Gambar (JPG/PNG)", type=["jpg", "jpeg", "png", "webp"])
    
    img_ref_mode = None
    pil_image = None
    
    if uploaded_file:
        # Tampilkan gambar dan pilihan mode
        st.image(uploaded_file, caption="Preview Referensi", width=250)
        pil_image = Image.open(uploaded_file) # Buka gambar dengan PIL
        
        img_ref_mode = st.radio(
            "🎯 Mode Referensi Gambar:",
            ["🎨 Style Ref (Ambil Gaya)", "📦 Object Ref (Ambil Subjek)", "🔄 Variation (Buat Ulang)"],
            help="Style: Terapkan gaya gambar ini ke topik teks Anda.\nObject: Pertahankan objek gambar ini, tapi ubah background sesuai teks.\Variation: Buat variasi kreatif dari gambar ini."
        )
    # ----------------------------------

with col2:
    category = st.radio("🎯 Kategori Output:", ["Object Slice (PNG Assets)", "Social Media (IG/TikTok)", "Print Media (Flyer/Banner)"])
    
    if ai_platform == "Midjourney v6":
        if category == "Object Slice (PNG Assets)": ar_display = "--ar 1:1"
        elif category == "Social Media (IG/TikTok)": ar_display = st.selectbox("📐 Rasio", ["--ar 9:16 (Reels)", "--ar 4:5 (Feed)"])
        else: ar_display = st.selectbox("📐 Rasio", ["--ar 16:9 (Land)", "--ar 2:3 (Port)", "--ar 3:2 (Land)", "--ar 4:3 (Magz)"])
        ar_instr = f"Add {ar_display.split(' ')[0] + ' ' + ar_display.split(' ')[1]} at end."
        limit_msg = "Safe Limit: ~1800 chars"
    else:
        st.info(f"ℹ️ {ai_platform}: Atur rasio manual di web.")
        ar_instr = "Describe composition explicitly."
        limit_msg = "Hard Limit: 2000 chars"
        
    qty = st.slider("🔢 Jumlah Variasi", 1, 10, 5)
    st.caption(f"🛡️ {limit_msg}")

st.markdown("---")

# ==========================================
# 6. EKSEKUSI MULTIMODAL
# ==========================================
if st.button(f"🚀 Generate ({ai_platform})", type="primary"):
    
    keys_data = st.session_state.active_keys_data
    
    # Validasi Input yang lebih kompleks
    if not keys_data:
        st.error("⛔ Validasi Key dulu di Sidebar!")
        st.stop()
        
    # Jika tidak ada gambar, topik wajib diisi. Jika ada gambar variation, topik opsional.
    if not uploaded_file and not topic:
        st.warning("⚠️ Masukkan Topik atau Upload Gambar.")
        st.stop()
        
    # --- PROSES TRANSLATE (Jika ada topik) ---
    english_topic = ""
    if topic:
        with st.spinner("🌍 Menerjemahkan topik..."):
            translator_key = keys_data[0]['key']
            translator_model = keys_data[0]['model']
            english_topic = translate_topic(topic, translator_key, translator_model)
            st.markdown(f"<div class='translated-text'>🇺🇸 EN Context: {english_topic}</div>", unsafe_allow_html=True)
    # ------------------------------------------

    results = []
    st.sidebar.markdown("---")
    st.sidebar.caption("📉 Status Proses")
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
                # Model Flash/Pro 1.5 mendukung input gambar (multimodal)
                model = genai.GenerativeModel(current_data['model'])
                
                limit_instr = "CRITICAL: Output must be under 1800 chars. Concise & Dense."
                
                # --- RACIKAN PROMPT MULTIMODAL ---
                # Base role & task
                base_prompt = f"""
                Role: {ai_platform.split(' ')[0]} Expert Prompter.
                Task: Create a detailed image prompt.
                Category: {category}. Angle: {angle}.
                RULES: Commercial stock quality. {ar_instr} {limit_instr}
                OUTPUT: Raw prompt text only.
                """
                
                # Logika jika ADA GAMBAR
                if uploaded_file and pil_image:
                    if img_ref_mode.startswith("🎨 Style"):
                        vision_instr = f"""
                        VISION TASK: Analyze the uploaded image's STYLE (lighting, color palette, texture, mood).
                        APPLY that style to this new subject: "{english_topic}".
                        Do not copy the image's subject, only its aesthetic vibes.
                        """
                    elif img_ref_mode.startswith("📦 Object"):
                        vision_instr = f"""
                        VISION TASK: Identify the main OBJECT/SUBJECT in the uploaded image. Keep its appearance.
                        PLACE that object into a new context/environment based on: "{english_topic}" and Angle: {angle}.
                        """
                    else: # Variation
                        vision_instr = f"""
                        VISION TASK: Create a creative VARIATION of the uploaded image. Keep core identity but change composition slightly based on Angle: {angle}.
                        (Context hint if any: "{english_topic}")
                        """
                    # INPUT KE GEMINI: [Teks Instruksi, Data Gambar PIL]
                    final_input = [base_prompt + vision_instr, pil_image]
                    
                # Logika jika HANYA TEKS
                else:
                    text_instr = f"""
                    TASK: Create image prompt for Subject: "{english_topic}". Angle: {angle}.
                    """
                    final_input = base_prompt + text_instr

                # KIRIM KE GEMINI (Bisa Teks saja atau Teks+Gambar)
                response = model.generate_content(final_input, safety_settings=SAFETY)
                # -----------------------------------------
                
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
        st.success(f"✅ Selesai! {len(results)} Prompt Vision.")
        
        ref_status = f"IMAGE REF: {img_ref_mode}" if uploaded_file else "NO IMAGE REF"
        txt_out = f"PLATFORM: {ai_platform}\nTOPIK: {topic} ({english_topic})\n{ref_status}\n\n"
        for idx, r in enumerate(results):
            txt_out += f"[{r[0]}]\n{r[1]}\n\n"
        
        st.download_button("📥 Download .txt", txt_out, f"prompts_vision.txt")
        
        for idx, (ang, txt) in enumerate(results):
            char_len = len(txt)
            color = "green" if char_len < 1800 else "orange" if char_len < 2000 else "red"
            st.markdown(f"**#{idx+1} {ang}**")
            st.code(txt, language="text")
            st.markdown(f"<div class='char-count' style='color:{color}'>Length: {char_len} chars</div>", unsafe_allow_html=True)
    else:
        st.error("❌ Gagal Total. Cek Sidebar.")

# --- UPDATE LOG ---
st.sidebar.markdown("---")
with st.sidebar.expander("ℹ️ Update v5.0 (Vision)"):
    st.markdown("""
    - 👁️ **Image Input:** Upload referensi gambar.
    - 🎨 **Style Ref Mode:** Tiru gaya gambar lain.
    - 📦 **Object Ref Mode:** Pertahankan subjek, ubah latar.
    - 🔄 **Variation Mode:** Buat variasi kreatif.
    - 🌍 **Auto-Translate:** Masih berfungsi.
    """)
