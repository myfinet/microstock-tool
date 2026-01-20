import streamlit as st
import time
import random
import json
import os
from datetime import datetime
from PIL import Image

# ==========================================
# 1. SETUP & CONFIGURATION
# ==========================================
st.set_page_config(
    page_title="Microstock Gen v5.1 (History)",
    page_icon="🕒",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .stCodeBlock {margin-bottom: 0px;}
    div[data-testid="stExpander"] {border: 1px solid #e0e0e0; border-radius: 8px;}
    .char-count {font-size: 12px; color: #666; margin-top: 5px; font-family: monospace;}
    .translated-text {font-size: 14px; font-weight: bold; color: #2e7bcf; background-color: #f0f8ff; padding: 8px; border-radius: 5px; border: 1px solid #cce5ff; margin-bottom: 15px;}
    .history-item {font-size: 12px; border-bottom: 1px solid #eee; padding: 5px 0;}
</style>
""", unsafe_allow_html=True)

try:
    import google.generativeai as genai
    from google.generativeai.types import HarmCategory, HarmBlockThreshold
except ImportError:
    st.error("❌ Library Error. Requirements: google-generativeai>=0.8.3")
    st.stop()

# ==========================================
# 2. SISTEM MANAJEMEN HISTORI (DATABASE LOKAL)
# ==========================================
HISTORY_FILE = "key_history.json"

def load_history():
    """Membaca file history JSON"""
    if not os.path.exists(HISTORY_FILE):
        return {}
    try:
        with open(HISTORY_FILE, 'r') as f:
            return json.load(f)
    except:
        return {}

def save_to_history(api_key, model_name):
    """Menyimpan/Update key ke history dengan timestamp"""
    history = load_history()
    
    # Simpan dengan format dictionary
    history[api_key] = {
        "model": model_name,
        "last_used": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "Active"
    }
    
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=4)

def delete_history():
    if os.path.exists(HISTORY_FILE):
        os.remove(HISTORY_FILE)

# ==========================================
# 3. FUNGSI UTILITIES
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
        
        for m in candidates:
            if 'flash' in m and '1.5' in m: found_model = m; break
        if not found_model:
            for m in candidates:
                if 'pro' in m and '1.5' in m: found_model = m; break
        if not found_model and candidates: found_model = candidates[0]
            
        if not found_model: return False, "No Model Found", None

        model = genai.GenerativeModel(found_model)
        model.generate_content("Hi", generation_config={'max_output_tokens': 1})
        
        # JIKA SUKSES -> SIMPAN KE HISTORY OTOMATIS
        save_to_history(api_key, found_model)
        
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
# 4. SIDEBAR: KEY MANAGER & HISTORY
# ==========================================
st.sidebar.title("🔑 Key Manager")

if 'active_keys_data' not in st.session_state:
    st.session_state.active_keys_data = []

# --- TAB NAVIGASI SIDEBAR ---
tab_input, tab_history = st.sidebar.tabs(["📝 Input Baru", "🕒 Riwayat"])

with tab_input:
    raw_input = st.text_area("Paste API Keys:", height=100, placeholder="AIzaSy...")
    if st.button("🔍 Validasi & Simpan", type="primary"):
        candidates = clean_keys(raw_input)
        if not candidates:
            st.error("❌ Key kosong.")
        else:
            valid_data = []
            progress = st.progress(0)
            status = st.empty()
            
            for i, key in enumerate(candidates):
                status.text(f"Cek Key {i+1}...")
                is_alive, msg, model_name = check_key_health(key)
                if is_alive:
                    valid_data.append({'key': key, 'model': model_name})
                progress.progress((i + 1) / len(candidates))
                
            st.session_state.active_keys_data = valid_data
            status.empty()
            
            if valid_data:
                st.success(f"🎉 {len(valid_data)} Key Disimpan!")
            else:
                st.error("💀 Semua Key Gagal.")

with tab_history:
    history_data = load_history()
    if history_data:
        st.caption(f"Tersimpan: {len(history_data)} Key")
        
        # Tombol Pakai Semua
        if st.button("♻️ Pakai Semua Key Riwayat"):
            loaded_keys = []
            for k, v in history_data.items():
                loaded_keys.append({'key': k, 'model': v['model']})
            st.session_state.active_keys_data = loaded_keys
            st.success(f"Berhasil memuat {len(loaded_keys)} key!")
            time.sleep(1)
            st.rerun()

        # Tombol Hapus
        if st.button("🗑️ Hapus Riwayat", type="secondary"):
            delete_history()
            st.rerun()

        st.markdown("---")
        # Tampilkan List
        for k, v in history_data.items():
            masked_key = f"...{k[-6:]}"
            last_used = v.get('last_used', '-')
            model_short = v['model'].split('/')[-1]
            
            st.markdown(f"""
            <div class='history-item'>
                <b>🔑 {masked_key}</b><br>
                <span style='color:green'>● {model_short}</span><br>
                <span style='color:#666'>🕒 {last_used}</span>
            </div>
            """, unsafe_allow_html=True)
            
    else:
        st.info("Belum ada riwayat key.")

# INDIKATOR STATUS AKTIF
if st.session_state.active_keys_data:
    st.sidebar.markdown("---")
    st.sidebar.success(f"🟢 **{len(st.session_state.active_keys_data)} Key Siap Digunakan**")
else:
    st.sidebar.markdown("---")
    st.sidebar.warning("🔴 Tidak ada Key Aktif")

# ==========================================
# 5. LOGIKA UTAMA (ANGLES & PROMPTING)
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
# 6. UI UTAMA (GENERATOR)
# ==========================================
st.title("👁️ Microstock Gen v5.1")
st.caption("Vision Support • Auto-History • Multi-Platform")

ai_platform = st.radio("🤖 Platform:", ["Midjourney v6", "Flux.1", "Ideogram 2.0"], horizontal=True)

col1, col2 = st.columns([1.2, 1])

with col1:
    topic = st.text_input("💡 Topik (Auto-Translate)", placeholder="Contoh: Kucing pakai helm")
    st.markdown("---")
    uploaded_file = st.file_uploader("🖼️ Upload Referensi Gambar (Opsional)", type=["jpg", "png", "webp"])
    
    img_ref_mode = None
    pil_image = None
    
    if uploaded_file:
        st.image(uploaded_file, width=200)
        pil_image = Image.open(uploaded_file)
        img_ref_mode = st.radio("🎯 Mode Referensi:", ["🎨 Style Ref", "📦 Object Ref", "🔄 Variation"])

with col2:
    category = st.radio("🎯 Kategori Output:", ["Object Slice (PNG Assets)", "Social Media (IG/TikTok)", "Print Media (Flyer/Banner)"])
    
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
        st.error("⛔ Load Key dari Riwayat atau Input Baru dulu!")
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
                
                # UPDATE TIMESTAMP DI BACKGROUND
                save_to_history(current_data['key'], current_data['model'])
                
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
