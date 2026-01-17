import streamlit as st
import google.generativeai as genai
import json
import time
import re

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(
    page_title="Microstock Prompt Engine", 
    page_icon="🚀", 
    layout="wide"
)

# --- 2. DEFINISI MODE VISUAL ---
VISUAL_MODES = {
    "1": {"name": "Isolated Object (Siap Slice)", "keywords": "white background, studio lighting, no shadow, isolated on white", "ar": "--ar 1:1"},
    "2": {"name": "Copy Space (Space Iklan)", "keywords": "minimalist, wide shot, rule of thirds, negative space on the side", "ar": "--ar 16:9"},
    "3": {"name": "Social Media Aesthetic", "keywords": "top down view, knolling, aesthetic lighting, instagram style, flatlay", "ar": "--ar 4:5"},
    "4": {"name": "Doodle & Line Art", "keywords": "thick outline, black and white, coloring book style, sticker design, vector style", "ar": "--ar 1:1"},
    "5": {"name": "Infographic & Isometric", "keywords": "isometric view, 3d vector render, gradient glass texture, tech startup vibe, --no text letters", "ar": "--ar 16:9"}
}

# --- 3. LOGIKA API KEY ---
def load_api_keys():
    keys = []
    source = "Manual"
    try:
        if "api_keys" in st.secrets:
            val = st.secrets["api_keys"]
            if isinstance(val, list): keys = [str(k).strip() for k in val if str(k).strip()]
            elif isinstance(val, str): keys = [k.strip() for k in val.split(',') if k.strip()]
            source = "Secrets"
    except: pass
    return keys, source

API_KEYS, key_source = load_api_keys()

# Sidebar
st.sidebar.header("🚀 Konfigurasi Model")
if API_KEYS:
    st.sidebar.success(f"✅ {len(API_KEYS)} Key Terdeteksi ({key_source})")
else:
    st.sidebar.warning("⚠️ Secrets Kosong.")
    raw = st.sidebar.text_area("Input Manual API Keys", height=100)
    if raw: API_KEYS = [k.strip() for k in raw.split(',') if k.strip()]

# PILIHAN MODEL (Auto Fallback)
# Kita prioritaskan Gemini 2.0 Flash Experimental (Terbaru & Tercepat)

MODELS_PRIORITY = [
    "gemini-1.5-flash",       # <--- PINDAHKAN INI KE PALING ATAS (Lebih Stabil)
    "gemini-1.5-flash-latest",
    "gemini-2.0-flash-exp",   # <--- Turunkan ini ke bawah (Cuma buat cadangan)
    "gemini-pro"
]

# --- 4. FUNGSI SMART GENERATOR ---
def clean_json(text):
    """Membersihkan output AI agar jadi JSON murni."""
    try:
        # Cari text di antara kurung kurawal pertama dan terakhir
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match: return json.loads(match.group(0))
    except: pass
    return None

def generate_with_fallback(model_instance, prompt):
    """Mencoba generate, jika model 404, coba model lain."""
    try:
        response = model_instance.generate_content(prompt)
        return response
    except Exception as e:
        raise e

def run_generation(topic, mode_key, trend, qty):
    mode = VISUAL_MODES[mode_key]
    results = []
    
    progress_bar = st.progress(0)
    status_log = st.empty()
    
    key_idx = 0
    
    # Deteksi Model yang bekerja (Hanya dilakukan sekali di awal)
    active_model_name = MODELS_PRIORITY[0] 
    
    for i in range(qty):
        status_log.info(f"🚀 Memproses {i+1}/{qty} menggunakan {active_model_name}...")
        success = False
        attempts = 0
        
        while not success and attempts < len(API_KEYS) * 2: # Kesempatan retry 2x putaran
            current_key = API_KEYS[key_idx]
            genai.configure(api_key=current_key)
            
            # LOOP MENCARI MODEL YANG COCOK (Flash 2.0 -> Flash 1.5 -> Pro)
            for model_name in MODELS_PRIORITY:
                try:
                    model = genai.GenerativeModel(model_name)
                    
                    sys_prompt = f"""
                    Role: Expert Microstock Prompter.
                    Task: Write 1 Midjourney prompt.
                    Topic: "{topic}". Style: "{mode['name']}" {trend}.
                    Mandatory: {mode['keywords']} {mode['ar']} --v 6.0
                    
                    OUTPUT JSON ONLY: {{ "prompt": "your description here" }}
                    """
                    
                    response = model.generate_content(sys_prompt)
                    
                    # Jika berhasil sampai sini, berarti model ini VALID
                    active_model_name = model_name # Ingat model ini untuk selanjutnya
                    
                    data = clean_json(response.text)
                    if data and 'prompt' in data:
                        final_p = data['prompt'].replace('/imagine prompt:', '').strip()
                        results.append(final_p)
                        success = True
                        break # Keluar dari loop model, lanjut ke prompt berikutnya
                    
                except Exception as e:
                    err = str(e)
                    # Jika errornya 404 (Model not found), lanjut ke model berikutnya di list
                    if "404" in err or "not found" in err:
                        continue 
                    # Jika error Limit (429), break loop model, ganti Key
                    elif "429" in err:
                        break 
                    # Jika error lain, lanjut coba model backup
                    else:
                        continue
            
            if success:
                # Geser key untuk load balancing
                key_idx = (key_idx + 1) % len(API_KEYS)
                time.sleep(1.5 if len(API_KEYS) > 1 else 4) # Delay pintar
                break # Keluar dari loop retry
            else:
                # Jika semua model gagal di key ini, ganti key
                key_idx = (key_idx + 1) % len(API_KEYS)
                attempts += 1
                time.sleep(1)
        
        if not success:
            st.error(f"❌ Gagal pada prompt #{i+1}. Cek kuota API Key Anda.")
            break
            
        progress_bar.progress((i + 1) / qty)
        
    status_log.success(f"✅ Selesai! Menggunakan engine: {active_model_name}")
    return results

# --- 5. UI UTAMA ---
st.title("🚀 Microstock Engine (Gemini 2.0 Ready)")
st.caption("Support Auto-Switch ke Gemini 2.0 Flash / 1.5 Flash")

col1, col2 = st.columns(2)
with col1:
    topic = st.text_input("💡 Topik", "Imlek Kuda Api")
    mode = st.selectbox("🎨 Mode", list(VISUAL_MODES.keys()), format_func=lambda x: VISUAL_MODES[x]['name'])
with col2:
    trend = st.text_input("📈 Trend", "")
    qty = st.number_input("🔢 Jumlah", 1, 100, 5)

if st.button("🚀 Generate Prompts", type="primary"):
    if not API_KEYS:
        st.error("API Key Kosong!")
    else:
        res = run_generation(topic, mode, trend, qty)
        if res:
            # Download TXT
            txt = "\n\n".join([f"{i+1}. {p}" for i,p in enumerate(res)])
            st.download_button("📥 Download .txt", txt, "prompts.txt")
            
            # Tampilan Copy-Paste
            st.markdown("---")
            for i, p in enumerate(res):
                st.write(f"**Prompt #{i+1}**")
                st.code(p, language="text")

