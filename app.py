import streamlit as st
import time
import random

# ==========================================
# 1. SETUP & LIBRARY
# ==========================================
st.set_page_config(
    page_title="Microstock Gen (Complete)",
    page_icon="⚡",
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
    st.error("❌ Library Error. Requirements: google-generativeai>=0.8.3")
    st.stop()

# ==========================================
# 2. FUNGSI VALIDASI
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
    """Cek Key DAN simpan nama model yang berhasil"""
    try:
        genai.configure(api_key=api_key, transport='rest')
        
        # Cari Model
        models = list(genai.list_models())
        found_model = None
        candidates = [m.name for m in models if 'generateContent' in m.supported_generation_methods]
        
        # Prioritas Model
        for m in candidates:
            if 'flash' in m and '1.5' in m: found_model = m; break
        if not found_model:
            for m in candidates:
                if 'pro' in m and '1.5' in m: found_model = m; break
        if not found_model and candidates:
            found_model = candidates[0]
            
        if not found_model: return False, "No Model Found", None

        # Test Ping
        model = genai.GenerativeModel(found_model)
        model.generate_content("Hi", generation_config={'max_output_tokens': 1})
        
        return True, "Active", found_model

    except Exception as e:
        err = str(e)
        if "429" in err: return False, "Quota Limit", None
        if "400" in err: return False, "Invalid Key", None
        return False, f"Error: {err[:15]}...", None

# ==========================================
# 3. SIDEBAR: VALIDASI
# ==========================================
st.sidebar.header("🔑 API Key Manager")

if 'active_keys_data' not in st.session_state:
    st.session_state.active_keys_data = []

raw_input = st.sidebar.text_area("Paste API Keys:", height=100, placeholder="AIzaSy...")

if st.sidebar.button("🔍 Validasi & Sync Model", type="primary"):
    candidates = clean_keys(raw_input)
    
    if not candidates:
        st.sidebar.error("❌ Key kosong.")
    else:
        valid_data = []
        progress_bar = st.sidebar.progress(0)
        status_text = st.sidebar.empty()
        
        st.sidebar.markdown("---")
        
        for i, key in enumerate(candidates):
            status_text.text(f"Cek Key {i+1}...")
            is_alive, msg, model_name = check_key_health(key)
            
            if is_alive:
                st.sidebar.success(f"Key {i+1}: OK")
                valid_data.append({'key': key, 'model': model_name})
            else:
                st.sidebar.error(f"Key {i+1}: {msg}")
            
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
# 4. LOGIKA UTAMA
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
# 5. UI GENERATOR
# ==========================================
st.title("⚡ Microstock Gen (Verified)")

ai_platform = st.radio("🤖 Platform:", ["Midjourney v6", "Flux.1", "Ideogram 2.0"], horizontal=True)

col1, col2 = st.columns(2)
with col1:
    topic = st.text_input("💡 Topik", placeholder="Contoh: Fresh Croissant")
    category = st.radio("🎯 Kategori:", ["Object Slice (PNG Assets)", "Social Media (IG/TikTok)", "Print Media (Flyer)"])

with col2:
    if ai_platform == "Midjourney v6":
        if category == "Object Slice (PNG Assets)": ar_display = "--ar 1:1"
        elif category == "Social Media (IG/TikTok)": ar_display = st.selectbox("📐 Rasio", ["--ar 9:16", "--ar 4:5"])
        else: ar_display = st.selectbox("📐 Rasio", ["--ar 2:3", "--ar 3:2"])
        ar_instr = f"Add {ar_display} at end."
    else:
        st.info(f"ℹ️ {ai_platform}: Atur rasio manual di webnya.")
        ar_instr = "Describe composition explicitly."
        
    qty = st.slider("🔢 Jumlah Variasi", 1, 10, 5)

st.markdown("---")

# ==========================================
# 6. EKSEKUSI
# ==========================================
if st.button(f"🚀 Generate Prompts ({ai_platform})", type="primary"):
    
    keys_data = st.session_state.active_keys_data
    
    if not keys_data:
        st.error("⛔ Validasi Key dulu di Sidebar!")
    elif not topic:
        st.warning("⚠️ Masukkan Topik.")
    else:
        results = []
        error_log = st.expander("📜 Log Error (Buka jika gagal)", expanded=False)
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
                    
                    if ai_platform == "Midjourney v6":
                        sys_prompt = f"""
                        Role: Midjourney Expert v6.
                        Task: Create 1 prompt for {category}. Subject: {topic}. Angle: {angle}.
                        RULES: Raw photography style, commercial stock quality.
                        Include parameters: --style raw --stylize 50 {ar_instr}
                        OUTPUT: Raw prompt text only.
                        """
                    elif ai_platform == "Flux.1":
                        sys_prompt = f"""
                        Role: Flux.1 Expert.
                        Task: Detailed image description for {category}. Subject: {topic}. Angle: {angle}.
                        RULES: Hyper-realistic, texture focus, natural language.
                        OUTPUT: Raw description only.
                        """
                    elif ai_platform == "Ideogram 2.0":
                        sys_prompt = f"""
                        Role: Ideogram Expert.
                        Task: Image description for {category}. Subject: {topic}. Angle: {angle}.
                        RULES: Focus on Composition, Visual Hierarchy.
                        OUTPUT: Raw description only.
                        """
                    
                    response = model.generate_content(sys_prompt, safety_settings=SAFETY)
                    
                    if response.text:
                        clean_p = response.text.strip().replace('"', '').replace("`", "").replace("Prompt:", "")
                        if ai_platform == "Midjourney v6" and "--style raw" not in clean_p:
                            clean_p += " --style raw"
                            
                        results.append((angle, clean_p))
                        success = True
                
                except Exception as e:
                    error_log.warning(f"Key #{key_idx+1}: {str(e)}")
                    pass
                
                key_idx = (key_idx + 1) % len(keys_data)
                if success: break
                else: attempts += 1
            
            pbar.progress((i+1)/qty)
        
        if results:
            st.success(f"✅ Selesai! {len(results)} Prompt.")
            
            # --- BAGIAN TOMBOL DOWNLOAD YANG HILANG (SUDAH DIKEMBALIKAN) ---
            txt_out = f"PLATFORM: {ai_platform}\nTOPIK: {topic}\n\n"
            for idx, r in enumerate(results):
                txt_out += f"[{r[0]}]\n{r[1]}\n\n"
            
            st.download_button(
                label="📥 Download .txt",
                data=txt_out,
                file_name=f"prompts_{topic}.txt",
                mime="text/plain"
            )
            # -------------------------------------------------------------
            
            for idx, (ang, txt) in enumerate(results):
                st.markdown(f"**#{idx+1} {ang}**")
                st.code(txt, language="text")
        else:
            st.error("❌ Gagal Total. Cek 'Log Error' di atas.")
