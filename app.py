import streamlit as st
import google.generativeai as genai
import sys

st.set_page_config(page_title="BARE METAL DEBUG", layout="wide")

st.title("💀 Debug Mode: Tanpa Ampun")
st.warning("Script ini tidak memiliki pengaman. Error akan muncul apa adanya.")

# 1. Tampilkan Versi Library (Wajib 0.8.3 ke atas)
try:
    lib_ver = genai.__version__
    st.write(f"📦 Library Version: `{lib_ver}`")
except:
    st.error("Library tidak terinstal dengan benar!")
    st.stop()

# 2. Input Satu Key Saja
api_key = st.text_input("Tempel 1 (SATU) API Key saja disini:", type="password")

# 3. Tombol Nekat
if st.button("🔥 TEST TEMBAK LANGSUNG"):
    if not api_key:
        st.error("Key kosong.")
    else:
        st.write("1. Mengonfigurasi API...")
        # Konfigurasi langsung
        genai.configure(api_key=api_key.strip())
        
        st.write("2. Menyiapkan Model (gemini-1.5-flash)...")
        # Kita panggil model secara spesifik
        model = genai.GenerativeModel("gemini-1.5-flash")
        
        st.write("3. Mengirim Request ke Google...")
        # KIRIM REQUEST TANPA TRY-EXCEPT
        # Jika ini gagal, layar akan penuh tulisan merah. Screenshot itu!
        response = model.generate_content("Tes. Apakah kamu hidup?")
        
        st.success("✅ BERHASIL!")
        st.write("Respon AI:")
        st.info(response.text)
