import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# --- Sayfa Ayarları ---
st.set_page_config(page_title="Echt Nederlands", page_icon="🇳🇱")

st.title("🇳🇱 Hollandaca Dinleme Pratiği")
st.markdown("Gerçek videolarla Hollandaca öğren.")

# --- Google Sheets Bağlantısı ---
# Bu bağlantı otomatik olarak cache (önbellek) tutar, yani hızlıdır.
conn = st.connection("gsheets", type=GSheetsConnection)

# Veriyi oku (SQL benzeri bir yapıya gerek yok, direkt DataFrame olarak alıyoruz)
try:
    data = conn.read()
    # Eğer veri boş gelirse hata vermemesi için kontrol
    if data.empty:
        st.error("Veritabanı boş veya okunamadı.")
        st.stop()
except Exception as e:
    st.error(f"Google Sheets bağlantı hatası: {e}")
    st.stop()

# --- Filtreleme (Sidebar) ---
with st.sidebar:
    st.header("Ayarlar")
    # Mevcut seviyeleri veritabanından çekip listele
    seviyeler = data['seviye'].unique().tolist()
    secilen_seviye = st.selectbox("Seviye Seç:", seviyeler)

# Seçilen seviyeye göre soruları filtrele
filtrelenmis_sorular = data[data['seviye'] == secilen_seviye]

# --- Rastgele Bir Soru Getir ---
if st.button("Soru Getir 🎲"):
    # Rastgele bir satır seç
    soru = filtrelenmis_sorular.sample(1).iloc[0]
    st.session_state['current_question'] = soru
    st.session_state['cevap_gosterildi'] = False

# --- Soruyu Ekrana Bas ---
if 'current_question' in st.session_state:
    q = st.session_state['current_question']
    
    # 1. Video
    st.video(q['video_url'], start_time=int(q['start_time']))
    
    st.divider()
    
    # 2. Soru
    st.subheader("Boşluğu Doldur:")
    st.markdown(f"### {q['soru_metni']}")
    
    # 3. Cevap Kontrol
    kullanici_cevabi = st.text_input("Cevabınız:", key="cevap_input")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Kontrol Et ✅"):
            if kullanici_cevabi.lower().strip() == str(q['dogru_cevap']).lower().strip():
                st.success("Tebrikler! Doğru.")
                st.balloons()
            else:
                st.error("Yanlış cevap, tekrar dene.")
    
    with col2:
        if st.button("Cevabı Göster 👀"):
            st.info(f"Doğru Cevap: **{q['dogru_cevap']}**")