import streamlit as st
import time
import random

# ==========================================
# 1. SETUP & LIBRARY
# ==========================================
st.set_page_config(
    page_title="Microstock Gen (Validated)",
    page_icon="⚡",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .stCodeBlock {margin-bottom: 0px;}
    div[data-testid="stExpander"] {border: 1px solid #e0e0e0; border-radius: 8px;}
    .success-box {padding: 10px; background-color: #d4edda; color: #155724; border-radius: 5px; margin-bottom: 10px;}
    .error-box {padding: 10px; background-color: #f8d7da; color: #721c24; border-radius: 5px; margin-bottom: 10px;}
</style>
""", unsafe_allow_html=True)

try:
    import google.generativeai as genai
    from google.generativeai.types import HarmCategory, HarmBlockThreshold
except ImportError:
    st.error("❌ Library Error. Pastikan requirements.txt berisi: google-generativeai>=0.8.3")
    st.stop()

# ==========================================
# 2. FUNGSI VALIDASI (THE GATEKEEPER)
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
    """Melakukan tes ping ringan untuk memastikan key hidup"""
    try:
        genai.configure(api_key=api_key, transport='rest')
        
        # 1. Cek Model Available
        models = list(genai.list_models())
        model_name = None
        
        # Prioritas Flash -> Pro
        model_candidates = [m.name for m in models if 'generateContent' in m.supported_generation_methods]
        
        for m in model_candidates:
            if 'flash' in m and '1.5' in m: 
                model_name = m; break
        if not model_name and model_candidates: 
            model_name = model_candidates[0]
            
        if not model_name:
            return False, "No Model Found", None

        # 2. Cek Eksekusi (Ping) - Token sangat sedikit biar cepat
        model = genai.GenerativeModel(model_name)
        response = model.generate_content("Hi", generation_config={'max_output_tokens': 1})
        
        return True, "Active", model_name

    except Exception as e:
        err = str(e)
        if "429" in err: return False, "Quota Exceeded (Limit)", None
        if "400" in err: return False, "Invalid Key", None
        return False, "Error Connection", None

# ==========================================
# 3. SIDEBAR: VALIDASI DULUAN
# ==========================================
st.sidebar.header("🔑 API Key Manager")

if 'verified_keys' not in st.session_state:
    st.session_state.verified_keys = []

raw_input = st.sidebar.text_area("Paste API Keys:", height=100, placeholder="AIzaSy...")

# Tombol Cek
if st.sidebar.button("🔍 Validasi Kunci", type="primary"):
    candidates = clean_keys(raw_input)
    
    if not candidates:
        st.sidebar.error("❌ Tidak ada key terdeteksi.")
    else:
        valid_pool = []
        progress_bar = st.sidebar.progress(0)
        status_text = st.sidebar.empty()
        
        st.sidebar.markdown("---")
        st.sidebar.markdown("**Laporan Status:**")
        
        for i, key in enumerate(candidates):
            status_text.text(f"Mengecek Key {i+1}...")
            is_alive, msg, model_used = check_key_health(key)
            
            masked = f"...{key[-4:]}"
            if is_alive:
                st.sidebar.markdown(f"✅ Key {i+1} ({masked}): **OK**")
                valid_pool.append(key)
            else:
                st.sidebar.markdown(f"❌ Key {i+1} ({masked}): **{msg}**")
            
            progress_bar.progress((i + 1) / len(candidates))
            
        st.session_state.verified_keys = valid_pool
        status_text.empty()
        
        if valid_pool:
            st.sidebar.success(f"🎉 {len(valid_pool)} Key Siap Tempur!")
        else:
            st.sidebar.error("💀 Semua Key Mati/Limit.")

# Tampilkan Status Terkini (Persisten)
if st.session_state.verified_keys:
    st.sidebar.info(f"🟢 {len(st.session_state.verified_keys)} Key Aktif di Memori")
else:
    st.sidebar.warning("🔴 Belum ada Key Valid.")


# ==========================================
# 4. LOGIKA UTAMA (SAMA SEPERTI SEBELUMNYA)
# ==========================================

SAFETY = {
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
}

# --- ANGLES DATABASE ---
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
st.title("⚡ Microstock Gen (Verified Mode)")

# Platform Selector
ai_platform = st.radio("🤖 Target AI Platform:", ["Midjourney v6", "Flux.1", "Ideogram 2.0"], horizontal=True)

col1, col2 = st.columns(2)
with col1:
    topic = st.text_input("💡 Topik / Objek", placeholder="Contoh: Fresh Croissant")
    category = st.radio("🎯 Kategori:", ["Object Slice (PNG Assets)", "Social Media (IG/TikTok)", "Print Media (Flyer)"])

with col2:
    if ai_platform == "Midjourney v6":
        if category == "Object Slice (PNG Assets)": ar_display = "--ar 1:1"
        elif category == "Social Media (IG/TikTok)": ar_display = st.selectbox("📐 Rasio", ["--ar 9:16", "--ar 4:5"])
        else: ar_display = st.selectbox("📐 Rasio", ["--ar 2:3", "--ar 3:2"])
        ar_instr = f"Add {ar_display} at end."
    else:
        st.info(f"ℹ️ {ai_platform}: Atur rasio manual di aplikasi AI.")
        ar_instr = "Describe composition explicitly."
        
    qty = st.slider("🔢 Jumlah Variasi", 1, 10, 5)

st.markdown("---")

# ==========================================
# 6. EKSEKUSI (HANYA JIKA KEY VALID)
# ==========================================
if st.button(f"🚀 Generate Prompts ({ai_platform})", type="primary", use_container_width=True):
    
    # CEK KUNCI DULUAN
    valid_keys = st.session_state.verified_keys
    
    if not valid_keys:
        st.error("⛔ STOP! Silakan validasi API Key dulu di Sidebar sebelah kiri.")
    elif not topic:
        st.warning("⚠️ Masukkan Topik dulu.")
    else:
        results = []
        pbar = st.progress(0)
        status = st.empty()
        
        angles = get_angles(category, qty)
        key_idx = 0
        
        # Kita pakai Auto-Detect Model lagi di sini untuk instance
        # Tapi karena key sudah divalidasi, kemungkinan error kecil.
        
        for i in range(qty):
            angle = angles[i]
            status.text(f"⏳ Meracik Konsep {i+1}: {angle}...")
            
            # Kita anggap semua key di valid_pool itu bagus, tapi tetap pake try-except
            # jaga-jaga kalau limit habis pas tengah jalan
            success = False
            attempts = 0
            
            while not success and attempts < len(valid_keys):
                current_key = valid_keys[key_idx]
                
                try:
                    genai.configure(api_key=current_key, transport='rest')
                    model = genai.GenerativeModel("gemini-1.5-flash") # Default aman
                    
                    # PROMPT LOGIC
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
                        Role: Flux.1 Expert Photographer.
                        Task: Detailed image description for {category}. Subject: {topic}. Angle: {angle}.
                        RULES: Hyper-realistic, focus on texture, lighting, skin pores, material details. Natural language.
                        OUTPUT: Raw description only.
                        """
                    elif ai_platform == "Ideogram 2.0":
                        sys_prompt = f"""
                        Role: Ideogram Design Expert.
                        Task: Image description for {category}. Subject: {topic}. Angle: {angle}.
                        RULES: Focus on Composition, Visual Hierarchy, Typography space.
                        OUTPUT: Raw description only.
                        """
                    
                    response = model.generate_content(sys_prompt, safety_settings=SAFETY)
                    
                    if response.text:
                        clean_p = response.text.strip().replace('"', '').replace("`", "").replace("Prompt:", "")
                        if ai_platform == "Midjourney v6" and "--style raw" not in clean_p:
                            clean_p += " --style raw"
                            
                        results.append((angle, clean_p))
                        success = True
                
                except Exception:
                    # Kalau key ini gagal (tiba-tiba limit), kita tandai (opsional)
                    # dan pindah ke key berikutnya
                    pass
                
                key_idx = (key_idx + 1) % len(valid_keys)
                
                if success:
                    time.sleep(0.5)
                    break
                else:
                    attempts += 1
                    time.sleep(0.5)
            
            pbar.progress((i+1)/qty)
        
        status.empty()
        
        if results:
            st.success(f"✅ Selesai! {len(results)} Prompt Terbuat.")
            
            # Download
            txt_out = f"PLATFORM: {ai_platform}\nTOPIK: {topic}\n\n"
            for idx, r in enumerate(results):
                txt_out += f"[{r[0]}]\n{r[1]}\n\n"
            
            st.download_button("📥 Download .txt", txt_out, f"prompts_{topic}.txt")
            
            # Display
            for idx, (ang, txt) in enumerate(results):
                st.markdown(f"**#{idx+1} {ang}**")
                st.code(txt, language="text")
        else:
            st.error("❌ Gagal Generate. Kemungkinan Key Limit di tengah jalan.")
