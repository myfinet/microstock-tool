import streamlit as st
import google.generativeai as genai
import time
from google.generativeai.types import HarmCategory, HarmBlockThreshold

# ==========================================
# 1. KONFIGURASI HALAMAN & STYLE
# ==========================================
st.set_page_config(
    page_title="Microstock Prompt Pro",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS untuk tampilan lebih rapi
st.markdown("""
<style>
    .stCodeBlock {margin-bottom: 0px;}
    .reportview-container {background: #0e1117;}
    div[data-testid="stExpander"] div[role="button"] p {font-size: 1rem; font-weight: bold;}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. LOGIKA UTAMA (ENGINE)
# ==========================================

# A. Pembersih Key Otomatis
def clean_api_keys(raw_text):
    if not raw_text: return []
    # Ubah baris baru jadi koma, pisah koma, hapus spasi & kutip
    candidates = raw_text.replace('\n', ',').split(',')
    cleaned = []
    for c in candidates:
        k = c.strip().replace('"', '').replace("'", "")
        # Validasi format dasar Google Key
        if k.startswith("AIza") and len(k) > 30:
            cleaned.append(k)
    return list(set(cleaned)) # Hapus duplikat

# B. Auto-Discovery Model (Anti-404)
# Mencari model terbaik yang tersedia di akun, menggunakan protokol REST
@st.cache_resource
def get_best_model(_api_key):
    try:
        # Wajib pakai REST agar tembus firewall Streamlit
        genai.configure(api_key=_api_key, transport='rest')
        
        models = list(genai.list_models())
        available = [m.name for m in models if 'generateContent' in m.supported_generation_methods]
        
        # Prioritas Model (Flash -> Pro -> Apapun yang ada)
        for m in available:
            if 'flash' in m and '1.5' in m: return m
        for m in available:
            if 'flash' in m: return m
        for m in available:
            if 'pro' in m and '1.5' in m: return m
            
        return available[0] if available else "models/gemini-1.5-flash"
    except:
        return "models/gemini-1.5-flash" # Fallback

# C. Konfigurasi Safety (Agar prompt tidak diblokir sensor)
SAFETY_SETTINGS = {
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
}

# ==========================================
# 3. SIDEBAR: SETUP API
# ==========================================
st.sidebar.header("🔑 API Configuration")
st.sidebar.caption("Paste API Key Anda di bawah ini (bisa sekaligus banyak).")

# Menggunakan Session State agar key tidak hilang saat refresh/klik tombol
if 'api_keys' not in st.session_state:
    st.session_state.api_keys = []

raw_input = st.sidebar.text_area("API Keys:", height=150, help="Format: AIzaSy...", placeholder="Paste daftar key di sini...")

if raw_input:
    keys = clean_api_keys(raw_input)
    if keys:
        st.session_state.api_keys = keys
        st.sidebar.success(f"✅ {len(keys)} Key Siap Digunakan")
        
        # Deteksi Model di background
        active_model = get_best_model(keys[0])
        st.sidebar.info(f"🧠 Engine: `{active_model.split('/')[-1]}`")
    else:
        st.sidebar.error("❌ Format Key tidak valid (Harus diawali 'AIza')")

# ==========================================
# 4. PRESET MODE VISUAL (Optimized for Stock)
# ==========================================
VISUAL_MODES = {
    "isolated": {
        "label": "📦 Isolated Object (Asset)",
        "desc": "White background, clean cut, no shadow, commercial use",
        "prompt": "isolated on plain white background, studio lighting, commercial photography, ultra detailed, 8k, sharp focus, no shadow, --ar 1:1"
    },
    "copyspace": {
        "label": "📝 Copy Space (Background)",
        "desc": "Wide shot, minimalist, room for text placement",
        "prompt": "minimalist composition, wide angle, negative space on the side for text, soft lighting, professional stock photo, high resolution, --ar 16:9"
    },
    "flatlay": {
        "label": "📸 Flatlay / Social Media",
        "desc": "Top-down view, organized items, aesthetic",
        "prompt": "knolling photography, flat lay, top down view, aesthetic arrangement, soft shadows, instagram style, trending on pinterest, --ar 4:5"
    },
    "vector": {
        "label": "🎨 Vector / Illustration",
        "desc": "Flat design, sticker style, simple lines",
        "prompt": "vector art style, flat design, thick outline, sticker design, white background, adobe illustrator style, simple and clean, --ar 1:1"
    },
    "3d_icon": {
        "label": "🧊 3D Icon / Isometric",
        "desc": "Cute 3D render, clay texture or glass",
        "prompt": "3d isometric icon, claymorphism, soft gradient lighting, cute 3d render, c4d, blender style, colorful, --ar 1:1"
    }
}

# ==========================================
# 5. UI UTAMA
# ==========================================
st.title("🎨 Microstock Prompt Pro")
st.caption("Generate deskripsi prompt Midjourney yang optimasi untuk Adobe Stock & Freepik.")

col1, col2 = st.columns([1, 1])

with col1:
    topic = st.text_input("💡 Topik Utama / Objek", placeholder="Misal: Cute Chinese New Year Snake")
    trend = st.text_input("📈 Tambahan Trend / Style (Opsional)", placeholder="Misal: Pastel Color, Cyberpunk, Watercolor")

with col2:
    selected_mode = st.selectbox("🎨 Pilih Mode Visual", list(VISUAL_MODES.keys()), format_func=lambda x: VISUAL_MODES[x]['label'])
    qty = st.slider("🔢 Jumlah Prompt", min_value=1, max_value=20, value=5)

# Tampilkan info mode yang dipilih
st.info(f"ℹ️ **Info Mode:** {VISUAL_MODES[selected_mode]['desc']}")

# ==========================================
# 6. EKSEKUSI GENERATOR
# ==========================================
if st.button("🚀 Generate Prompts", type="primary", use_container_width=True):
    if not st.session_state.api_keys:
        st.error("⚠️ Harap masukkan API Key di Sidebar terlebih dahulu.")
    elif not topic:
        st.warning("⚠️ Harap isi Topik Utama.")
    else:
        # Persiapan Data
        mode_data = VISUAL_MODES[selected_mode]
        keys = st.session_state.api_keys
        results = []
        
        # UI Feedback
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Logic Loop
        key_idx = 0
        model_name = get_best_model(keys[0]) # Ambil model dari cache
        
        for i in range(qty):
            status_text.text(f"⏳ Sedang meracik prompt {i+1} dari {qty}...")
            
            success = False
            attempts = 0
            max_attempts = len(keys) # Jangan loop selamanya
            
            while not success and attempts < max_attempts:
                current_key = keys[key_idx]
                
                try:
                    # 1. Konfigurasi (REST PROTOCOL IS MANDATORY)
                    genai.configure(api_key=current_key, transport='rest')
                    model = genai.GenerativeModel(model_name)
                    
                    # 2. Prompt Engineering
                    # Kita minta AI hanya mengeluarkan prompt final tanpa basa-basi
                    sys_prompt = f"""
                    Role: Professional Microstock Prompter for Midjourney v6.
                    Task: Create 1 optimized prompt.
                    Subject: {topic}.
                    Style/Trend: {trend}.
                    Base Parameters (Mandatory): {mode_data['prompt']}
                    
                    Instructions:
                    - Combine the subject with the base parameters naturally.
                    - Ensure descriptions are visual and descriptive.
                    - OUTPUT ONLY THE RAW PROMPT TEXT. No "Here is the prompt", no quotes, no markdown blocks.
                    """
                    
                    # 3. Generate dengan Safety Settings OFF
                    response = model.generate_content(sys_prompt, safety_settings=SAFETY_SETTINGS)
                    
                    if response.text:
                        # Bersihkan sisa-sisa formatting jika AI bandel
                        clean_p = response.text.strip().replace('`', '').replace('"', '').replace("'", "")
                        if "prompt:" in clean_p.lower(): 
                            clean_p = clean_p.replace("Prompt:", "").replace("prompt:", "").strip()
                        
                        results.append(clean_p)
                        success = True
                        
                        # Load Balancing (Rotasi Key)
                        key_idx = (key_idx + 1) % len(keys)
                        time.sleep(0.5) # Jeda sopan agar tidak spamming
                        
                except Exception as e:
                    # Error Handling Senyap (Silent Failover)
                    # Kita hanya pindah key tanpa memunculkan error merah menakutkan ke user
                    key_idx = (key_idx + 1) % len(keys)
                    attempts += 1
                    time.sleep(1)
            
            if not success:
                st.warning(f"⚠️ Gagal membuat prompt ke-{i+1} (Koneksi sibuk).")
            
            progress_bar.progress((i + 1) / qty)
            
        status_text.empty()
        
        # ==========================================
        # 7. HASIL & DOWNLOAD
        # ==========================================
        if results:
            st.success(f"✅ Selesai! Berhasil membuat {len(results)} prompt.")
            
            # Area Download TXT
            txt_output = "\n\n".join([f"{p}" for p in results])
            st.download_button(
                label="📥 Download Semua (.txt)",
                data=txt_output,
                file_name=f"prompts_{topic.replace(' ', '_')}.txt",
                mime="text/plain",
                use_container_width=True
            )
            
            st.markdown("---")
            
            # Tampilan Copy-Paste yang User Friendly
            for idx, prompt in enumerate(results):
                st.markdown(f"**Prompt #{idx+1}**")
                st.code(prompt, language="text")
                st.caption("Klik icon 'Copy' di pojok kanan atas kotak kode.")
