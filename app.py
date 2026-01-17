import streamlit as st
import google.generativeai as genai
import json
import time
import re

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(
    page_title="Microstock Prompt Lite", 
    page_icon="🛠️", 
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

# --- 3. LOGIKA API KEY (SUPER AMAN) ---
def load_api_keys():
    keys = []
    source = "Manual"
    
    # Coba baca Secrets
    try:
        if "api_keys" in st.secrets:
            secret_val = st.secrets["api_keys"]
            # Jika List
            if isinstance(secret_val, list):
                keys = [str(k).strip() for k in secret_val if str(k).strip()]
                source = "Secrets (List)"
            # Jika String (dipisah koma)
            elif isinstance(secret_val, str):
                keys = [k.strip() for k in secret_val.split(',') if k.strip()]
                source = "Secrets (String)"
    except Exception as e:
        st.sidebar.error(f"⚠️ Gagal baca Secrets: {e}")

    return keys, source

API_KEYS, key_source = load_api_keys()

# Sidebar
st.sidebar.header("🛠️ Konfigurasi & Status")
if API_KEYS:
    st.sidebar.success(f"✅ {len(API_KEYS)} Key terdeteksi ({key_source})")
else:
    st.sidebar.warning("⚠️ Tidak ada Key di Secrets.")
    input_manual = st.sidebar.text_area("Input Key Manual (Pisahkan koma)", height=100)
    if input_manual:
        API_KEYS = [k.strip() for k in input_manual.split(',') if k.strip()]
        if API_KEYS: st.sidebar.success(f"✅ {len(API_KEYS)} Key Manual dipakai.")

# --- 4. FUNGSI EKSTRAK JSON (REGEX) ---
def extract_json(text_response):
    """Mencari pola {...} di dalam teks, mengabaikan teks sampah lainnya."""
    try:
        # Cari text yang diawali kurung kurawal { dan diakhiri }
        match = re.search(r'\{.*\}', text_response, re.DOTALL)
        if match:
            json_str = match.group(0)
            return json.loads(json_str)
        else:
            return None
    except Exception:
        return None

# --- 5. FUNGSI GENERATOR ---
def run_generation(topic, mode_key, trend, qty):
    mode_data = VISUAL_MODES[mode_key]
    results = []
    
    progress_bar = st.progress(0)
    status_box = st.empty()
    error_box = st.container() # Area khusus log error
    
    key_index = 0
    current_delay = 4.0 if len(API_KEYS) < 2 else 1.0 # Lebih cepat jika banyak key
    
    for i in range(qty):
        status_box.info(f"🔄 Sedang memproses prompt {i+1} / {qty}...")
        success = False
        attempts = 0
        max_attempts = len(API_KEYS) * 2 
        
        while not success and attempts < max_attempts:
            current_key_idx = (key_index + attempts) % len(API_KEYS)
            current_key = API_KEYS[current_key_idx]
            
            try:
                # Setup Model
                genai.configure(api_key=current_key)
                model = genai.GenerativeModel("gemini-1.5-flash")
                
                # Prompt Engineering
                sys_prompt = f"""
                You are a prompt generator.
                Task: Create 1 Midjourney prompt for Topic: "{topic}", Style: "{mode_data['name']}" {f', Trend: {trend}' if trend else ''}.
                Mandatory: {mode_data['keywords']} {mode_data['ar']} --v 6.0
                
                IMPORTANT: Return ONLY a valid JSON format like this:
                {{ "prompt": "your prompt description here" }}
                """
                
                response = model.generate_content(sys_prompt)
                
                # Ekstraksi Data
                data = extract_json(response.text)
                
                if data and 'prompt' in data:
                    clean_p = data['prompt'].replace('/imagine prompt:', '').strip()
                    results.append(clean_p)
                    success = True
                    # Geser index key untuk prompt berikutnya (Load Balancing)
                    key_index = (current_key_idx + 1) % len(API_KEYS)
                    time.sleep(current_delay)
                else:
                    raise ValueError("AI tidak memberikan JSON valid.")
                
            except Exception as e:
                # TAMPILKAN ERROR NYATA DI LAYAR UNTUK DEBUGGING
                error_msg = str(e)
                # Sembunyikan sebagian key asli agar aman
                masked_key = current_key[:5] + "..." 
                
                if "429" in error_msg:
                    print(f"Key {masked_key} Limit Habis. Ganti key...")
                elif "400" in error_msg:
                    error_box.error(f"❌ Key Invalid ({masked_key}). Cek copas Anda!")
                else:
                    print(f"Error lain pada Key {masked_key}: {error_msg}")
                
                attempts += 1
                time.sleep(1) # Jeda sebentar sebelum retry
        
        if not success:
            st.error(f"❌ Gagal Total pada Prompt #{i+1}. Semua Key Error/Limit.")
            break
            
        progress_bar.progress((i + 1) / qty)
        
    status_box.empty()
    return results

# --- 6. UI UTAMA ---
st.title("🛠️ Microstock Prompt (Debug Mode)")
st.caption("Jika masih error, screenshot pesan merah yang muncul dan kirim ke saya.")

col1, col2 = st.columns(2)
with col1:
    topic = st.text_input("💡 Topik", "Imlek Kuda Api")
    mode_key = st.selectbox("🎨 Mode", list(VISUAL_MODES.keys()), format_func=lambda x: VISUAL_MODES[x]['name'])
with col2:
    trend = st.text_input("📈 Trend", "")
    qty = st.number_input("🔢 Jumlah", 1, 100, 5)

if st.button("🚀 Generate Prompts", type="primary"):
    if not API_KEYS:
        st.error("🚫 API Key Kosong! Masukkan di Sidebar atau Secrets.")
    else:
        results = run_generation(topic, mode_key, trend, qty)
        
        if results:
            st.success(f"Berhasil membuat {len(results)} prompt!")
            
            # Area Download
            txt_out = "\n\n".join([f"{i+1}. {p}" for i, p in enumerate(results)])
            st.download_button("📥 Download .txt", txt_out, f"prompts.txt")
            
            # Area Copy
            for i, p in enumerate(results):
                st.write(f"**Prompt #{i+1}**")
                st.code(p, language="text")
