import streamlit as st
import time
import random
import json
import os
from datetime import datetime
from PIL import Image

# ==========================================
# 1. SETUP & KONFIGURASI HALAMAN
# ==========================================
st.set_page_config(
    page_title="Microstock Gen v6.0 (Stable)",
    page_icon="💎",
    layout="wide"
)

# Custom CSS untuk tampilan bersih
st.markdown("""
<style>
    .stCodeBlock {margin-bottom: 0px;}
    div[data-testid="stExpander"] {border: 1px solid #e0e0e0; border-radius: 8px;}
    .char-count {font-size: 12px; color: #666; margin-top: 5px; font-family: monospace;}
    .translated-text {font-size: 14px; font-weight: bold; color: #2e7bcf; background-color: #f0f8ff; padding: 8px; border-radius: 5px; border: 1px solid #cce5ff; margin-bottom: 15px;}
    .status-ok {color: green; font-weight: bold;}
    .status-err {color: red; font-weight: bold;}
</style>
""", unsafe_allow_html=True)

try:
    import google.generativeai as genai
    from google.generativeai.types import HarmCategory, HarmBlockThreshold
except ImportError:
    st.error("❌ Library Error. Pastikan requirements.txt berisi: google-generativeai>=0.8.3 dan Pillow")
    st.stop()

# ==========================================
# 2. SISTEM CACHE (SIMPAN KEY OTOMATIS)
# ==========================================
CACHE_FILE = "api_cache.json"

def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r') as f:
                data = json.load(f)
                return data.get("keys", ""), data.get("timestamp", "")
        except:
            return "", ""
    return "", ""

def save_cache(keys_text):
    data = {
        "keys": keys_text,
        "timestamp": datetime.now().strftime("%d %B %Y, %H:%M")
    }
    with open(CACHE_FILE, 'w') as f:
        json.dump(data, f)

# ==========================================
# 3. CORE LOGIC (ANTI-ERROR & STABLE MODEL)
# ==========================================

def clean_keys(raw_text):
    if not raw_text: return []
    candidates = raw_text.replace('\n', ',').split(',')
    cleaned = []
    for c in candidates:
        k = c.strip().replace('"', '').replace("'", "")
        # Validasi dasar format key Google
        if k.startswith("AIza") and len(k) > 20:
            cleaned.append(k)
    return list(set(cleaned))

def get_stable_model(api_key):
    """
    Mencari model yang STABIL & GRATIS.
    Membuang versi '-exp' atau 'experimental'.
    """
    try:
        # WAJIB REST PROTOCOL (Fix Error 400/Connection)
        genai.configure(api_key=api_key, transport='rest')
        
        all_models = list(genai.list_models())
        candidates = [m.name for m in all_models if 'generateContent' in m.supported_generation_methods]
        
        # 1. Filter: Hapus model experimental
        stable_candidates = [m for m in candidates if 'exp' not in m.lower()]
        
        if not stable_candidates:
            # Jika terpaksa, ambil apa saja
            stable_candidates = candidates

        # 2. Prioritas: Flash 1.5 -> Pro 1.5 -> Pro 1.0
        # Flash 1.5 adalah yang terbaik untuk tier gratis saat ini
        found_model = None
        for m in stable_candidates:
            if 'flash' in m and '1.5' in m: found_model = m; break
        
        if not found_model:
            for m in stable_candidates:
                if 'pro' in m and '1.5' in m: found_model = m; break
        
        if not found_model and stable_candidates:
            found_model = stable_candidates[0]
            
        if not found_model:
            return False, "No Model Available", None

        # 3. Test Ping (1 Token)
        model = genai.GenerativeModel(found_model)
        model.generate_content("Hi", generation_config={'max_output_tokens': 1})
        
        return True, "Active", found_model

    except Exception as e:
        err = str(e)
        if "429" in err: return False, "Quota Limit (429)", None
        if "400" in err: return False, "Bad Request (400)", None
        return False, f"Error: {err[:15]}...", None

def translate_topic(text, api_key, model_name):
    """Translate Indo -> English menggunakan model yang valid"""
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
# 4. SIDEBAR (KEY MANAGER)
# ==========================================
st.sidebar.title("🔑 API Key")

cached_keys, last_time = load_cache()
raw_input = st.sidebar.text_area("Paste API Keys:", value=cached_keys, height=100, placeholder="AIzaSy...")

if last_time:
    st.sidebar.caption(f"🕒 Terakhir dipakai: {last_time}")

if 'active_keys_data' not in st.session_state:
    st.session_state.active_keys_data = []

# Tombol Validasi
if st.sidebar.button("Validasi Key (Wajib)", type="primary"):
    candidates = clean_keys(raw_input)
    if not candidates:
        st.sidebar.error("❌ Key kosong.")
    else:
        valid_data = []
        progress = st.sidebar.progress(0)
        status = st.sidebar.empty()
        
        for i, key in enumerate(candidates):
            status.text(f"Cek Key {i+1}...")
            is_alive, msg, model_name = get_stable_model(key)
            
            if is_alive:
                valid_data.append({'key': key, 'model': model_name})
            
            progress.progress((i + 1) / len(candidates))
            
        st.session_state.active_keys_data = valid_data
        status.empty()
        progress.empty()
        
        if valid_data:
            st.sidebar.success(f"✅ {len(valid_data)} Key Stabil")
            save_cache(raw_input)
            time.sleep(0.5)
            st.rerun()
        else:
            st.sidebar.error("💀 Semua Key Mati/Limit.")

# Indikator Status
if st.session_state.active_keys_data:
    st.sidebar.info(f"🟢 {len(st.session_state.active_keys_data)} Key Siap (Stable Model)")
else:
    if cached_keys:
        st.sidebar.warning("⚠️ Klik Validasi dulu.")

# ==========================================
# 5. CONSTANTS & DATABASE ANGLE
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
st.title("💎 Microstock Gen v6.0")
st.caption("Stable Core • Anti-429 • Vision Support")

ai_platform = st.radio("🤖 Platform:", ["Midjourney v6", "Flux.1", "Ideogram 2.0"], horizontal=True)

col1, col2 = st.columns([1.2, 1])

with col1:
    topic = st.text_input("💡 Topik (Auto-Translate)", placeholder="Contoh: Nasi goreng spesial")
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
        if category == "Object Slice (PNG Assets)": 
            ar_display = "--ar 1:1"
        elif category == "Social Media (IG/TikTok)": 
            ar_display = st.selectbox("📐 Rasio", ["--ar 9:16", "--ar 4:5"])
        else: 
            ar_display = st.selectbox("📐 Rasio", ["--ar 16:9", "--ar 2:3", "--ar 3:2", "--ar 4:3"])
        
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
# 7. EKSEKUSI (ANTI-PARALEL LOOP)
# ==========================================
if st.button(f"🚀 Generate ({ai_platform})", type="primary"):
    
    keys_data = st.session_state.active_keys_data
    
    # Validasi Awal
    if not keys_data:
        st.error("⛔ Key belum divalidasi! Cek Sidebar.")
        st.stop()
    if not uploaded_file and not topic:
        st.warning("⚠️ Isi Topik atau Upload Gambar.")
        st.stop()

    # 1. Translate Topic (Sequential)
    english_topic = ""
    if topic:
        with st.spinner("🌍 Menerjemahkan..."):
            # Pakai key pertama untuk translate
            english_topic = translate_topic(topic, keys_data[0]['key'], keys_data[0]['model'])
            st.markdown(f"<div class='translated-text'>🇺🇸 EN: {english_topic}</div>", unsafe_allow_html=True)

    results = []
    
    # Log Error di Sidebar agar UI bersih
    st.sidebar.markdown("---")
    error_log = st.sidebar.expander("📜 Log Error (Real-time)", expanded=False)
    
    pbar = st.progress(0)
    status_text = st.empty()
    
    angles = get_angles(category, qty)
    key_idx = 0 # Pointer Key
    
    # LOOP UTAMA (ANTI-PARALEL)
    # Kita tidak menggunakan ThreadPoolExecutor. Ini murni Loop Python biasa.
    # Ini menjamin request dikirim satu per satu (Max Workers = 1).
    
    for i in range(qty):
        angle = angles[i]
        status_text.text(f"⏳ Memproses {i+1}/{qty}: {angle}...")
        
        success = False
        attempts = 0
        max_attempts = len(keys_data) * 2 # Beri kesempatan 2x putaran key
        
        # LOOP RETRY (FAILOVER SYSTEM)
        while not success and attempts < max_attempts:
            current_data = keys_data[key_idx]
            
            try:
                # Konfigurasi Ulang (REST Wajib)
                genai.configure(api_key=current_data['key'], transport='rest')
                model = genai.GenerativeModel(current_data['model'])
                
                # --- Prompt Engineering ---
                limit_instr = "Output must be under 1800 chars. Concise."
                base_prompt = f"""
                Role: {ai_platform.split(' ')[0]} Expert.
                Task: Detailed image prompt.
                Category: {category}. Angle: {angle}.
                RULES: Commercial quality. {ar_instr} {limit_instr}
                OUTPUT: Raw prompt text only.
                """
                
                final_input = base_prompt
                if uploaded_file and pil_image:
                    # Logic Multimodal
                    if img_ref_mode.startswith("🎨 Style"):
                        vision_instr = f"Analyze STYLE. Apply to: '{english_topic}'."
                    elif img_ref_mode.startswith("📦 Object"):
                        vision_instr = f"Identify MAIN OBJECT. Place in new context: '{english_topic}'. Angle: {angle}."
                    else:
                        vision_instr = f"Create creative VARIATION. Context: '{english_topic}'."
                    final_input = [base_prompt + vision_instr, pil_image]
                else:
                    final_input = base_prompt + f"Subject: '{english_topic}'."

                # --- GENERATE REQUEST ---
                response = model.generate_content(final_input, safety_settings=SAFETY)
                
                if response.text:
                    clean_p = response.text.strip().replace('"', '').replace("`", "").replace("Prompt:", "")
                    
                    # Midjourney Fix
                    if ai_platform == "Midjourney v6" and "--style raw" not in clean_p:
                        clean_p += " --style raw"
                    
                    # Hard Limit Fix
                    if len(clean_p) > 2000: clean_p = clean_p[:1997] + "..."
                    
                    results.append((angle, clean_p))
                    success = True
            
            except Exception as e:
                err_msg = str(e)
                masked_key = f"...{current_data['key'][-4:]}"
                
                # Penanganan Error Spesifik
                if "429" in err_msg:
                    error_log.warning(f"Key {masked_key} Limit (429). Pause 5s...")
                    time.sleep(5) # Jeda Anti-Limit
                elif "404" in err_msg or "400" in err_msg:
                    error_log.error(f"Key {masked_key} Error (404/400). Ganti Key.")
                else:
                    error_log.warning(f"Key {masked_key} Error: {err_msg}")
                
                # GAGAL -> PINDAH KEY BERIKUTNYA
                key_idx = (key_idx + 1) % len(keys_data)
                attempts += 1
                
            # Jika berhasil, tetap rotasi key untuk Load Balancing
            if success:
                key_idx = (key_idx + 1) % len(keys_data)
                time.sleep(1) # Jeda natural antar prompt sukses
        
        pbar.progress((i+1)/qty)
    
    status_text.empty()
    
    # HASIL AKHIR
    if results:
        st.success(f"✅ Selesai! {len(results)} Prompt Berhasil.")
        
        ref_info = f"REF IMAGE: {img_ref_mode}" if uploaded_file else ""
        txt_out = f"PLATFORM: {ai_platform}\nTOPIK: {topic} ({english_topic})\n{ref_info}\n\n"
        for idx, r in enumerate(results):
            txt_out += f"[{r[0]}]\n{r[1]}\n\n"
        
        st.download_button("📥 Download .txt", txt_out, "prompts_final.txt")
        
        for idx, (ang, txt) in enumerate(results):
            char_len = len(txt)
            color = "green" if char_len < 1800 else "orange" if char_len < 2000 else "red"
            st.markdown(f"**#{idx+1} {ang}**")
            st.code(txt, language="text")
            st.caption(f"Panjang: {char_len} chars")
    else:
        st.error("❌ Gagal Total. Semua Key mungkin limit/habis.")
