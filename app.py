import streamlit as st
import google.generativeai as genai
import json
import time

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(
    page_title="Microstock Prompt Lite", 
    page_icon="⚡", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. DEFINISI DATA & MODE ---
VISUAL_MODES = {
    "1": {"name": "Isolated Object (Siap Slice)", "keywords": "white background, studio lighting, no shadow, isolated on white", "ar": "--ar 1:1"},
    "2": {"name": "Copy Space (Space Iklan)", "keywords": "minimalist, wide shot, rule of thirds, negative space on the side", "ar": "--ar 16:9"},
    "3": {"name": "Social Media Aesthetic", "keywords": "top down view, knolling, aesthetic lighting, instagram style, flatlay", "ar": "--ar 4:5"},
    "4": {"name": "Doodle & Line Art", "keywords": "thick outline, black and white, coloring book style, sticker design, vector style", "ar": "--ar 1:1"},
    "5": {"name": "Infographic & Isometric", "keywords": "isometric view, 3d vector render, gradient glass texture, tech startup vibe, --no text letters", "ar": "--ar 16:9"}
}

# --- 3. LOGIKA API KEY (ROBUST VERSION) ---
def load_api_keys():
    """Membaca API Key dari Secrets atau Input Manual dengan aman."""
    keys = []
    source = "Manual"
    
    # Cek Secrets (Prioritas Utama)
    if "api_keys" in st.secrets:
        secret_val = st.secrets["api_keys"]
        
        # Jika formatnya List: ["key1", "key2"]
        if isinstance(secret_val, list):
            keys = secret_val
            source = "Secrets (List)"
            
        # Jika formatnya String: "key1,key2,key3"
        elif isinstance(secret_val, str):
            # Pecah koma dan bersihkan spasi
            keys = [k.strip() for k in secret_val.split(',') if k.strip()]
            source = "Secrets (String)"
            
    return keys, source

# Load Keys saat aplikasi mulai
API_KEYS, key_source = load_api_keys()

# Tampilan Sidebar
st.sidebar.header("⚡ Konfigurasi API")

if API_KEYS:
    st.sidebar.success(f"✅ Terhubung via {key_source}")
    st.sidebar.text(f"Jumlah Key: {len(API_KEYS)}")
else:
    st.sidebar.warning("⚠️ Secrets kosong/tidak ditemukan.")
    st.sidebar.info("Masukkan API Key Manual di bawah:")
    input_manual = st.sidebar.text_area("Paste API Keys (Pisahkan koma)", height=100)
    if input_manual:
        API_KEYS = [k.strip() for k in input_manual.split(',') if k.strip()]
        if API_KEYS:
            st.sidebar.success(f"✅ {len(API_KEYS)} Key Manual Dimuat!")

# --- 4. FUNGSI GENERATOR AI ---
def get_model(api_key):
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(
        model_name="gemini-1.5-flash", 
        generation_config={"response_mime_type": "application/json"}
    )

def clean_json_text(text_response):
    """Membersihkan output jika AI menyertakan backticks markdown."""
    clean = text_response.strip()
    if clean.startswith("```json"):
        clean = clean[7:]
    if clean.startswith("```"):
        clean = clean[3:]
    if clean.endswith("```"):
        clean = clean[:-3]
    return clean.strip()

def create_sys_prompt(topic, mode_data, trend=""):
    return f"""
    Task: Create 1 Midjourney prompt description only.
    Topic: "{topic}"
    Style: "{mode_data['name']}" {f'+ Trend: {trend}' if trend else ''}
    Mandatory Params: {mode_data['keywords']} {mode_data['ar']} --v 6.0
    
    INSTRUCTION:
    - Do NOT use '/imagine prompt:' prefix.
    - Return output in strictly Valid JSON format: {{ "prompt": "your prompt text here" }}
    """

def run_generation(topic, mode_key, trend, qty):
    mode_data = VISUAL_MODES[mode_key]
    results = []
    
    # UI Component
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Logic Rotasi Key
    key_index = 0
    
    for i in range(qty):
        status_text.text(f"⚡ Sedang meracik prompt {i+1} dari {qty}...")
        success = False
        
        # Coba generate dengan key yang ada
        while not success and key_index < len(API_KEYS):
            current_key = API_KEYS[key_index]
            try:
                # 1. Init Model
                model = get_model(current_key)
                # 2. Kirim Prompt
                sys_msg = create_sys_prompt(topic, mode_data, trend)
                response = model.generate_content(sys_msg)
                
                # 3. Parsing JSON (dengan pembersih)
                clean_txt = clean_json_text(response.text)
                data = json.loads(clean_txt)
                
                # 4. Ambil Prompt Final
                final_prompt = data.get('prompt', 'Error parsing prompt')
                results.append(final_prompt)
                
                success = True
                time.sleep(5) # Jeda ringan
                
            except Exception as e:
                # print(f"Error Key-{key_index}: {e}") # Debugging Log
                key_index += 1 # Pindah ke key cadangan
        
        if not success:
            st.error(f"❌ Gagal pada prompt ke-{i+1}. Semua API Key limit atau error.")
            break
            
        progress_bar.progress((i + 1) / qty)
        
    status_text.empty()
    return results

# --- 5. ANTARMUKA UTAMA (UI) ---
st.title("⚡ Microstock Prompt Lite")
st.markdown("---")

# Form Input
col1, col2 = st.columns(2)
with col1:
    topic = st.text_input("💡 Topik Utama", placeholder="Contoh: Imlek Kuda Api")
    mode_key = st.selectbox("🎨 Mode Visual", list(VISUAL_MODES.keys()), format_func=lambda x: VISUAL_MODES[x]['name'])
with col2:
    trend = st.text_input("📈 Trend (Opsional)", placeholder="Contoh: Cyberpunk, Pastel")
    qty = st.number_input("🔢 Jumlah Prompt", min_value=1, max_value=100, value=5)

# Tombol Eksekusi
if st.button("🚀 Generate Prompts", type="primary"):
    if not API_KEYS:
        st.error("⚠️ API Key belum dimasukkan! Cek Sidebar.")
    elif not topic:
        st.error("⚠️ Topik wajib diisi.")
    else:
        with st.spinner("AI sedang bekerja..."):
            prompts = run_generation(topic, mode_key, trend, qty)
            
            if prompts:
                st.success(f"Selesai! {len(prompts)} prompt berhasil dibuat.")
                
                # --- A. AREA DOWNLOAD (TXT) ---
                txt_buffer = ""
                for idx, p in enumerate(prompts, 1):
                    txt_buffer += f"{idx}. {p}\n\n"
                    
                st.download_button(
                    label="📥 Download File .txt",
                    data=txt_buffer,
                    file_name=f"prompts_{topic.replace(' ', '_')}.txt",
                    mime="text/plain"
                )
                
                st.markdown("---")
                st.subheader("📋 Hasil Prompt (Siap Copy)")
                
                # --- B. AREA TAMPILAN 1 BLOK 1 TOMBOL COPY ---
                for idx, p in enumerate(prompts, 1):
                    st.write(f"**Prompt #{idx}**")
                    # st.code otomatis membuat blok kode dengan tombol copy di kanan atas
                    st.code(p, language="text")
