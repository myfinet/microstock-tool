import streamlit as st
import google.generativeai as genai
import json
import time
import re

# ==========================================
# 1. KONFIGURASI HALAMAN
# ==========================================
st.set_page_config(
    page_title="Microstock Prompt Engine",
    page_icon="🎨",
    layout="wide"
)

# ==========================================
# 2. DEFINISI MODE VISUAL
# ==========================================
VISUAL_MODES = {
    "1": {"name": "Isolated Object (Siap Slice)", "keywords": "white background, studio lighting, no shadow, isolated on white, high quality", "ar": "--ar 1:1"},
    "2": {"name": "Copy Space (Space Iklan)", "keywords": "minimalist, wide shot, rule of thirds, negative space on the side", "ar": "--ar 16:9"},
    "3": {"name": "Social Media Aesthetic", "keywords": "top down view, knolling, aesthetic lighting, instagram style, flatlay", "ar": "--ar 4:5"},
    "4": {"name": "Doodle & Line Art", "keywords": "thick outline, black and white, coloring book style, sticker design, vector style, simple", "ar": "--ar 1:1"},
    "5": {"name": "Infographic & Isometric", "keywords": "isometric view, 3d vector render, gradient glass texture, tech startup vibe, --no text letters", "ar": "--ar 16:9"}
}

# Prioritas Model (Stabil diutamakan)
MODEL_PRIORITY = [
    "gemini-1.5-flash",       # Paling Stabil & Cepat
    "gemini-1.5-flash-latest",# Alternatif nama
    "gemini-pro",             # Cadangan Legacy
]

# ==========================================
# 3. LOGIKA API KEY & SECRETS (ROBUST)
# ==========================================
def load_api_keys():
    keys = []
    source = "Manual Input"
    
    # Coba baca dari Secrets
    if "api_keys" in st.secrets:
        try:
            secret_val = st.secrets["api_keys"]
            # Jika format List
            if isinstance(secret_val, list):
                keys = [str(k).strip() for k in secret_val if str(k).strip()]
                source = "Secrets (List)"
            # Jika format String ("key1,key2")
            elif isinstance(secret_val, str):
                keys = [k.strip() for k in secret_val.split(',') if k.strip()]
                source = "Secrets (String)"
        except Exception:
            pass # Abaikan error parsing, biarkan kosong agar masuk manual

    return keys, source

API_KEYS, key_source = load_api_keys()

# Sidebar Status
st.sidebar.header("⚙️ Konfigurasi API")
if API_KEYS:
    st.sidebar.success(f"✅ Terhubung via {key_source}")
    st.sidebar.caption(f"Jumlah Key: {len(API_KEYS)}")
else:
    st.sidebar.warning("⚠️ Secrets Kosong / Tidak Terbaca")
    st.sidebar.info("Masukkan API Key Manual (Pisahkan dengan koma):")
    manual_input = st.sidebar.text_area("API Keys", height=100, placeholder="AIzaSy..., AIzaSy...")
    if manual_input:
        API_KEYS = [k.strip() for k in manual_input.split(',') if k.strip()]
        if API_KEYS: st.sidebar.success(f"✅ {len(API_KEYS)} Key Manual Dimuat")

# ==========================================
# 4. FUNGSI GENERATOR PINTAR
# ==========================================
def extract_json(text):
    """Mengambil JSON valid dari respon AI yang mungkin kotor."""
    try:
        # Cari pola {...} menggunakan Regex
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
    except:
        return None
    return None

def run_generation(topic, mode_key, trend, qty):
    mode = VISUAL_MODES[mode_key]
    results = []
    
    # UI Progress
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    key_idx = 0
    current_delay = 1.5 if len(API_KEYS) > 1 else 4.0 # Otomatis atur kecepatan
    
    for i in range(qty):
        status_text.text(f"⏳ Sedang meracik prompt #{i+1} dari {qty}...")
        success = False
        attempts = 0
        max_attempts = len(API_KEYS) * 2 # Beri kesempatan 2x putaran kunci
        
        while not success and attempts < max_attempts:
            # Rotasi Key
            current_key = API_KEYS[key_idx]
            
            # Loop Model Fallback (Coba Flash -> kalau gagal -> Coba Pro)
            model_success = False
            for model_name in MODEL_PRIORITY:
                if model_success: break # Jika sudah sukses di model sebelumnya, stop loop model
                
                try:
                    genai.configure(api_key=current_key)
                    model = genai.GenerativeModel(model_name)
                    
                    # Prompt System (Hemat Token)
                    sys_prompt = f"""
                    Role: Expert Prompt Engineer.
                    Task: Create 1 Midjourney prompt description ONLY.
                    Context: Topic "{topic}", Style "{mode['name']}" {f', Trend "{trend}"' if trend else ''}.
                    Requirements: {mode['keywords']} {mode['ar']} --v 6.0
                    
                    Instruction: Return ONLY valid JSON format: {{ "prompt": "your prompt here" }}
                    """
                    
                    response = model.generate_content(sys_prompt)
                    
                    # Parsing JSON
                    data = extract_json(response.text)
                    if data and 'prompt' in data:
                        clean_prompt = data['prompt'].replace('/imagine prompt:', '').strip()
                        results.append(clean_prompt)
                        
                        success = True
                        model_success = True
                        
                        # Pindah ke key berikutnya untuk load balancing
                        key_idx = (key_idx + 1) % len(API_KEYS)
                        time.sleep(current_delay)
                        
                except Exception as e:
                    # Logika Error Handling Senyap
                    err_msg = str(e)
                    # Jika error Limit (429), break loop model, ganti key
                    if "429" in err_msg:
                        break 
                    # Jika model not found (404), continue ke model berikutnya
                    elif "404" in err_msg or "not found" in err_msg:
                        continue
                    else:
                        continue

            if success:
                break # Lanjut ke prompt berikutnya (i+1)
            else:
                # Ganti Key dan coba lagi
                key_idx = (key_idx + 1) % len(API_KEYS)
                attempts += 1
                time.sleep(1) # Jeda panic

        if not success:
            st.error(f"❌ Gagal membuat Prompt #{i+1}. Semua Key/Model sibuk.")
            break
            
        progress_bar.progress((i + 1) / qty)
        
    status_text.empty()
    return results

# ==========================================
# 5. ANTARMUKA UTAMA (UI)
# ==========================================
st.title("🎨 Microstock Prompt Engine")
st.markdown("---")

col1, col2 = st.columns(2)
with col1:
    topic = st.text_input("💡 Topik Utama", placeholder="Misal: Chinese New Year Fire Horse")
    mode_key = st.selectbox("🎨 Mode Visual", list(VISUAL_MODES.keys()), format_func=lambda x: VISUAL_MODES[x]['name'])
with col2:
    trend = st.text_input("📈 Trend Injector (Opsional)", placeholder="Misal: Pastel Color, Cyberpunk")
    qty = st.number_input("🔢 Jumlah Prompt", min_value=1, max_value=100, value=5)

if st.button("🚀 Generate Prompts", type="primary"):
    # Validasi Input
    if not API_KEYS:
        st.error("⚠️ API Key belum terdeteksi! Masukkan di Sidebar atau atur Secrets.")
    elif not topic:
        st.error("⚠️ Topik wajib diisi!")
    else:
        with st.spinner("Sedang bekerja dengan AI..."):
            prompts = run_generation(topic, mode_key, trend, qty)
            
            if prompts:
                st.success(f"Selesai! Berhasil membuat {len(prompts)} prompt.")
                
                # --- BAGIAN DOWNLOAD TXT ---
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
                
                # --- BAGIAN TAMPILAN 1 BLOK 1 TOMBOL COPY ---
                for idx, p in enumerate(prompts, 1):
                    st.write(f"**Prompt #{idx}**")
                    # st.code otomatis memunculkan tombol copy di pojok kanan atas
                    st.code(p, language="text")
