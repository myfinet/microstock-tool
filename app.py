import streamlit as st
import time
import random
import sys

# ==========================================
# 1. SETUP & SAFE IMPORTS
# ==========================================
st.set_page_config(page_title="Microstock Brain V3", page_icon="🧠", layout="wide")

# Coba import library dengan aman
try:
    import google.generativeai as genai
    from google.generativeai.types import HarmCategory, HarmBlockThreshold
    STABLE_IMPORT = True
except ImportError:
    st.error("❌ Library Error: `google-generativeai` belum terinstal atau versi terlalu lama.")
    st.info("Cek file requirements.txt Anda.")
    STABLE_IMPORT = False

# ==========================================
# 2. LOGIKA UTAMA
# ==========================================

# Daftar Angle untuk variasi
STOCK_ANGLES = [
    "Business Concept (Office, planning, corporate)",
    "Modern Technology (Gadgets, screens, future)",
    "Culinary (Food, ingredients, dining)",
    "Lifestyle (Family, friends, authentic moments)",
    "Abstract Background (Texture, bokeh, pattern)",
    "Education (Books, learning, school)",
    "Health (Yoga, medical, wellness)",
    "Home & Interior (Cozy, decoration, furniture)",
    "Travel (Outdoor, landscape, adventure)",
    "Creative Art (Paint, surreal, artistic)"
]

def get_random_angles(qty):
    # Ambil angle acak
    if qty > len(STOCK_ANGLES):
        base = STOCK_ANGLES * (qty // len(STOCK_ANGLES) + 1)
        return random.sample(base, qty)
    return random.sample(STOCK_ANGLES, qty)

# Pembersih Key
def clean_keys(raw):
    if not raw: return []
    cleaned = []
    # Ganti baris baru jadi koma
    parts = raw.replace('\n', ',').split(',')
    for p in parts:
        k = p.strip().replace('"', '').replace("'", "")
        if k.startswith("AIza") and len(k) > 20:
            cleaned.append(k)
    return list(set(cleaned))

# Konfigurasi Safety (PENTING AGAR TIDAK DIBLOKIR)
SAFETY = {
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
}

# ==========================================
# 3. SIDEBAR
# ==========================================
st.sidebar.header("🧠 Setup Key")
input_keys = st.sidebar.text_area("Paste API Keys:", height=150, placeholder="AIzaSy...")

# Simpan keys di session state
if 'my_keys' not in st.session_state:
    st.session_state.my_keys = []

if input_keys:
    valid_keys = clean_keys(input_keys)
    if valid_keys:
        st.session_state.my_keys = valid_keys
        st.sidebar.success(f"✅ {len(valid_keys)} Key Siap")
    else:
        st.sidebar.error("❌ Format Key Salah")

# ==========================================
# 4. DATA MODE VISUAL
# ==========================================
VISUAL_MODES = {
    "photo": {"label": "📸 Photorealistic", "prompt": "photorealistic, 8k, highly detailed, canon r5, commercial lighting"},
    "3d": {"label": "🧊 3D Render", "prompt": "3d render, cinema 4d, isometric, cute style, soft lighting, --ar 1:1"},
    "vector": {"label": "🎨 Flat Vector", "prompt": "flat vector illustration, white background, simple shapes, sticker style, --ar 1:1"},
    "minimal": {"label": "⚪ Minimalist", "prompt": "minimalist photography, negative space, soft colors, clean composition, --ar 16:9"}
}

# ==========================================
# 5. UI & GENERATOR
# ==========================================
st.title("🧠 Microstock Brain V3 (Anti-Crash)")

col1, col2 = st.columns(2)
with col1:
    topic = st.text_input("💡 Topik", "Ramadhan")
    trend = st.text_input("📈 Trend (Opsional)", "Modern Islamic")
with col2:
    mode_key = st.selectbox("🎨 Gaya Visual", list(VISUAL_MODES.keys()), format_func=lambda x: VISUAL_MODES[x]['label'])
    qty = st.slider("🔢 Jumlah Variasi", 1, 15, 5)

if st.button("🚀 Generate (Klik Sekali)", type="primary"):
    if not st.session_state.my_keys:
        st.error("⚠️ Masukkan Key di Sidebar dulu!")
    elif not topic:
        st.warning("⚠️ Masukkan Topik!")
    elif not STABLE_IMPORT:
        st.error("⚠️ Library Google belum terinstal benar.")
    else:
        # MULAI PROSES
        results = []
        logs = st.expander("📜 Lihat Log Error (Jika ada yg gagal)", expanded=False)
        pbar = st.progress(0)
        
        keys = st.session_state.my_keys
        angles = get_random_angles(qty)
        mode_data = VISUAL_MODES[mode_key]['prompt']
        
        key_idx = 0
        
        for i in range(qty):
            angle = angles[i]
            success = False
            attempts = 0
            
            while not success and attempts < len(keys):
                current_key = keys[key_idx]
                masked_key = f"...{current_key[-4:]}"
                
                try:
                    # 1. Konfigurasi (REST WAJIB)
                    genai.configure(api_key=current_key, transport='rest')
                    # Kita pakai model auto-detect sederhana
                    model = genai.GenerativeModel("gemini-1.5-flash")
                    
                    # 2. Prompt
                    full_prompt = f"""
                    Role: Stock Photographer.
                    Topic: {topic}.
                    Concept Angle: {angle}.
                    Visual Style: {mode_data} {trend}.
                    
                    Instructions:
                    - Combine the topic with the concept angle.
                    - Avoid generic descriptions.
                    - Output ONLY the prompt text.
                    """
                    
                    # 3. Generate (Safety OFF)
                    response = model.generate_content(full_prompt, safety_settings=SAFETY)
                    
                    # 4. CEK HASIL DENGAN HATI-HATI (ANTI-CRASH)
                    # Kita cek apakah ada candidates, bukan langsung .text
                    if response.candidates and response.candidates[0].content.parts:
                        final_text = response.text.strip().replace('"','').replace("`","")
                        results.append((angle.split('(')[0], final_text))
                        success = True
                    else:
                        # Jika respon ada tapi kosong (biasanya kena filter)
                        logs.warning(f"⚠️ Prompt {i+1} diblokir Google (Safety Filter). Mencoba key lain...")
                        # Jangan break, coba key lain siapa tahu bisa
                        
                except Exception as e:
                    err = str(e)
                    if "429" in err:
                        pass # Limit, coba key lain
                    elif "404" in err:
                        # Jika model flash gak ada, coba pro
                        try:
                            model = genai.GenerativeModel("gemini-pro")
                            response = model.generate_content(full_prompt, safety_settings=SAFETY)
                            if response.text:
                                results.append((angle.split('(')[0], response.text.strip()))
                                success = True
                        except:
                            pass
                    else:
                        logs.error(f"❌ Error Key {masked_key}: {err}")
                
                # Pindah key
                key_idx = (key_idx + 1) % len(keys)
                
                if success:
                    break
                else:
                    attempts += 1
                    time.sleep(0.5)
            
            pbar.progress((i+1)/qty)
        
        # TAMPILKAN HASIL
        if results:
            st.success(f"✅ Berhasil membuat {len(results)} dari {qty} prompt.")
            st.markdown("---")
            
            # Download
            txt_content = "\n\n".join([f"[{r[0]}] {r[1]}" for r in results])
            st.download_button("📥 Download .txt", txt_content, "prompts.txt")
            
            for idx, (ang, txt) in enumerate(results):
                st.markdown(f"**#{idx+1} Konsep: {ang}**")
                st.code(txt, language="text")
        else:
            st.error("❌ Gagal total. Cek 'Log Error' di atas untuk detailnya.")
