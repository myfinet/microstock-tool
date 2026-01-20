import streamlit as st
import time
import random

# ==========================================
# 1. SETUP & LIBRARY
# ==========================================
st.set_page_config(
    page_title="Microstock Gen v4.6",
    page_icon="⚡",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .stCodeBlock {margin-bottom: 0px;}
    div[data-testid="stExpander"] {border: 1px solid #e0e0e0; border-radius: 8px;}
    .char-count {font-size: 12px; color: #666; margin-top: 5px; font-family: monospace;}
</style>
""", unsafe_allow_html=True)

try:
    import google.generativeai as genai
    from google.generativeai.types import HarmCategory, HarmBlockThreshold
except ImportError:
    st.error("❌ Library Error. Requirements: google-generativeai>=0.8.3")
    st.stop()

# ==========================================
# 2. FUNGSI VALIDASI & UTILITIES
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
        
        # Prioritas Model (Flash -> Pro -> Default)
        for m in candidates:
            if 'flash' in m and '1.5' in m: found_model = m; break
        if not found_model:
            for m in candidates:
                if 'pro' in m and '1.5' in m: found_model = m; break
        if not found_model and candidates: found_model = candidates[0]
            
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
# 3. SIDEBAR: INPUT & VALIDASI
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
# 4. LOGIKA UTAMA (SAFETY & ANGLES)
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
# 5. UI GENERATOR (MAIN AREA)
# ==========================================
st.title("⚡ Microstock Gen v4.6")
st.caption("Adobe Stock & Freepik Compliant • Multi-Platform Engine")

ai_platform = st.radio("🤖 Platform:", ["Midjourney v6", "Flux.1", "Ideogram 2.0"], horizontal=True)

col1, col2 = st.columns(2)
with col1:
    topic = st.text_input("💡 Topik", placeholder="Contoh: Fresh Croissant")
    category = st.radio("🎯 Kategori:", ["Object Slice (PNG Assets)", "Social Media (IG/TikTok)", "Print Media (Flyer/Banner)"])

with col2:
    if ai_platform == "Midjourney v6":
        if category == "Object Slice (PNG Assets)": 
            ar_display = "--ar 1:1"
        elif category == "Social Media (IG/TikTok)": 
            ar_display = st.selectbox("📐 Rasio", ["--ar 9:16 (Reels/TikTok)", "--ar 4:5 (IG Feed)"])
        else: 
            # === UPDATE: MENAMBAHKAN 16:9 ===
            ar_display = st.selectbox("📐 Rasio", [
                "--ar 16:9 (Landscape Print/TV)",
                "--ar 2:3 (Poster/Flyer)", 
                "--ar 3:2 (Banner/Landscape)", 
                "--ar 4:3 (Majalah)"
            ])
            # =================================
        
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
# 6. EKSEKUSI & SIDEBAR FOOTER
# ==========================================
if st.button(f"🚀 Generate ({ai_platform})", type="primary"):
    
    keys_data = st.session_state.active_keys_data
    
    if not keys_data:
        st.error("⛔ Validasi Key dulu di Sidebar!")
    elif not topic:
        st.warning("⚠️ Masukkan Topik.")
    else:
        results = []
        
        # --- LOG ERROR (Dynamic) ---
        st.sidebar.markdown("---")
        st.sidebar.caption("📉 Status Proses")
        error_log = st.sidebar.expander("📜 Log Error (Real-time)", expanded=False)
        # ---------------------------
        
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
                    
                    limit_instr = "CRITICAL: Output must be under 1800 chars. Concise & Dense."
                    
                    if ai_platform == "Midjourney v6":
                        sys_prompt = f"""
                        Role: Midjourney Expert v6.
                        Task: Create 1 prompt for {category}. Subject: {topic}. Angle: {angle}.
                        RULES: Commercial stock quality.
                        Include parameters: --style raw --stylize 50 {ar_instr}
                        {limit_instr}
                        OUTPUT: Raw prompt text only.
                        """
                    elif ai_platform == "Flux.1":
                        sys_prompt = f"""
                        Role: Flux.1 Expert.
                        Task: Detailed image description for {category}. Subject: {topic}. Angle: {angle}.
                        RULES: Hyper-realistic, texture focus.
                        {limit_instr}
                        OUTPUT: Raw description only.
                        """
                    elif ai_platform == "Ideogram 2.0":
                        sys_prompt = f"""
                        Role: Ideogram Expert.
                        Task: Image description for {category}. Subject: {topic}. Angle: {angle}.
                        RULES: Focus on Composition & Typography space.
                        {limit_instr}
                        OUTPUT: Raw description only.
                        """
                    
                    response = model.generate_content(sys_prompt, safety_settings=SAFETY)
                    
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
            
            txt_out = f"PLATFORM: {ai_platform}\nTOPIK: {topic}\n\n"
            for idx, r in enumerate(results):
                txt_out += f"[{r[0]}]\n{r[1]}\n\n"
            
            st.download_button("📥 Download .txt", txt_out, f"prompts_{topic}.txt")
            
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
with st.sidebar.expander("ℹ️ Keterangan Update v4.6"):
    st.markdown("""
    **New Update:**
    - 📐 **Ratio 16:9:** Ditambahkan pada Print Media.
    - 🤖 **Multi-Platform:** Support Midjourney v6, Flux.1, Ideogram 2.0.
    - 🛡️ **Adobe Compliant:** Logika Concept Diversification.
    - 📏 **Limit Karakter:** Auto-limit <2000 chars.
    - 🔄 **Auto-Sync Model:** Validasi key pintar.
    """)
