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

# --- 3. LOGIKA API KEY (SUPER ROBUST) ---
def load_api_keys():
    """Membaca API Key dari Secrets atau Input Manual dengan penanganan error ganda."""
    keys = []
    source = "Manual"
    
    # Cek Secrets (Prioritas Utama)
    try:
        if "api_keys" in st.secrets:
            secret_val = st.secrets["api_keys"]
            
            # SKENARIO A: Format List (TOML array) -> ["key1", "key2"]
            if isinstance(secret_val, list):
                keys = [str(k).strip() for k in secret_val if str(k).strip()]
                source = "Secrets (List)"
                
            # SKENARIO B: Format String -> "key1,key2,key3"
            elif isinstance(secret_val, str):
                # Pecah berdasarkan koma, hapus spasi kiri/kanan
                keys = [k.strip() for k in secret_val.split(',') if k.strip()]
                source = "Secrets (String)"
    except Exception as e:
        st.sidebar.error(f"Error membaca Secrets: {e}")

    return keys, source

# Load Keys saat aplikasi mulai
API_KEYS, key_source = load_api_keys()

# Tampilan Sidebar
st.sidebar.header("⚡ Konfigurasi API")

if API_KEYS:
    st.sidebar.success(f"✅ Terhubung via {key_source}")
    st.sidebar.info(f"🔑 {len(API_KEYS)} Key Aktif\n⚡ Kecepatan: {len(API_KEYS) * 15} prompt/menit")
else:
    st.sidebar.warning("⚠️ Secrets kosong/tidak ditemukan.")
    st.sidebar.markdown("**Opsi Cadangan (Manual):**")
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
    """Pembersih output JSON dari AI."""
    clean = text_response.strip()
    # Hapus markdown ```json jika ada
    if clean.startswith("```json"): clean = clean[7:]
    elif clean.startswith("```"): clean = clean[3:]
    if clean.endswith("```"): clean = clean[:-3]
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
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    key_index = 0
    
    # --- PENGATURAN KECEPATAN (DELAY) ---
    # Jika 1 Key: Delay 4 detik (Sangat aman)
    # Jika 3 Key: Delay 1.5 detik (Cepat tapi Aman)
    current_delay = 4.0 if len(API_KEYS) < 2 else 1.5
    
    for i in range(qty):
        status_text.text(f"⚡ Meracik prompt {i+1} dari {qty}...")
        success = False
        
        # Retry Logic (Rotasi Key)
        attempts = 0
        max_attempts = len(API_KEYS) * 2 # Kesempatan mencoba 2x putaran kunci
        
        while not success and attempts < max_attempts:
            # Pastikan index tidak melebihi jumlah key (Looping/Modulo)
            current_key_idx = (key_index + attempts) % len(API_KEYS)
            current_key = API_KEYS[current_key_idx]
            
            try:
                model = get_model(current_key)
                sys_msg = create_sys_prompt(topic, mode_data, trend)
                response = model.generate_content(sys_msg)
                
                clean_txt = clean_json_text(response.text)
                data = json.loads(clean_txt)
                
                final_prompt = data.get('prompt', 'Error parsing prompt')
                results.append(final_prompt)
                
                success = True
                # Update key index global agar request selanjutnya pakai key berikutnya
                key_index = (current_key_idx + 1) % len(API_KEYS)
                
                # Jeda Waktu Aman
                time.sleep(current_delay) 
                
            except Exception as e:
                # print(f"Key-{current_key_idx} gagal. Coba key lain...") # Debug
                attempts += 1 # Coba key berikutnya
        
        if not success:
            st.error(f"❌ Gagal pada prompt ke-{i+1}. Semua API Key sedang sibuk/limit.")
            break
            
        progress_bar.progress((i + 1) / qty)
        
    status_text.empty()
    return results

# --- 5. ANTARMUKA UTAMA (UI) ---
st.title("⚡ Microstock Prompt Lite")
st.markdown("---")

col1, col2 = st.columns(2)
with col1:
    topic = st.text_input("💡 Topik Utama", placeholder="Contoh: Imlek Kuda Api")
    mode_key = st.selectbox("🎨 Mode Visual", list(VISUAL_MODES.keys()), format_func=lambda x: VISUAL_MODES[x]['name'])
with col2:
    trend = st.text_input("📈 Trend (Opsional)", placeholder="Contoh: Cyberpunk, Pastel")
    qty = st.number_input("🔢 Jumlah Prompt", min_value=1, max_value=100, value=5)

if st.button("🚀 Generate Prompts", type="primary"):
    if not API_KEYS:
        st.error("⚠️ API Key belum dimasukkan! Cek Sidebar atau Secrets.")
    elif not topic:
        st.error("⚠️ Topik wajib diisi.")
    else:
        with st.spinner("AI sedang bekerja..."):
            prompts = run_generation(topic, mode_key, trend, qty)
            
            if prompts:
                st.success(f"Selesai! {len(prompts)} prompt berhasil dibuat.")
                
                # DOWNLOAD TXT
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
                st.subheader("📋 Hasil Prompt")
                
                # TAMPILAN BLOK KODE (Sesuai Request)
                for idx, p in enumerate(prompts, 1):
                    st.write(f"**Prompt #{idx}**")
                    st.code(p, language="text")
