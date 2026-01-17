import streamlit as st
import google.generativeai as genai
import sys

st.set_page_config(page_title="System Check", page_icon="🩺")

st.title("🩺 Cek Kesehatan Server & API")

# --- 1. CEK VERSI LIBRARY ---
st.subheader("1. Versi Sistem")
st.write(f"Python Version: `{sys.version.split()[0]}`")
try:
    ver = genai.__version__
    st.write(f"Google Generative AI Version: `{ver}`")
    
    # Analisa Versi
    major, minor, patch = map(int, ver.split('.'))
    if minor < 7:
        st.error("❌ VERSI KADALUARSA! (Di bawah 0.7.0)")
        st.warning("👉 SOLUSI: Buat file 'requirements.txt' di GitHub dan isi dengan: google-generativeai>=0.8.3")
    else:
        st.success("✅ Versi Library OK (Sudah mendukung Gemini Flash)")
        
except Exception as e:
    st.error(f"Gagal cek versi: {e}")

# --- 2. INPUT API KEY ---
st.subheader("2. Tes Koneksi API")
api_key = st.text_input("Masukkan 1 API Key saja untuk tes:", type="password")

if st.button("Uji Koneksi & List Model"):
    if not api_key:
        st.error("Masukkan key dulu.")
    else:
        try:
            genai.configure(api_key=api_key)
            
            # Coba ambil list model
            st.write("Menghubungi Google...")
            models = list(genai.list_models())
            
            st.success("✅ Koneksi Berhasil!")
            st.write(f"Ditemukan {len(models)} model tersedia untuk Key ini.")
            
            # Cari model Flash
            flash_found = False
            available_names = []
            
            st.markdown("### Daftar Model yang Bisa Dipakai:")
            for m in models:
                if 'generateContent' in m.supported_generation_methods:
                    available_names.append(m.name)
                    st.code(m.name)
                    if "flash" in m.name:
                        flash_found = True
            
            if flash_found:
                st.success("🎉 Model 'Flash' DITEMUKAN! Aplikasi utama Anda pasti jalan sekarang.")
            else:
                st.warning("⚠️ Model Flash tidak ditemukan di list, tapi model lain ada.")
                
        except Exception as e:
            st.error("❌ KONEKSI GAGAL")
            st.error(f"Error Detail: {e}")
            st.info("Jika errornya '403', berarti Key salah atau Project di Google Cloud bermasalah.")
            st.info("Jika errornya '400 User Location', berarti IP Server Streamlit diblokir.")
