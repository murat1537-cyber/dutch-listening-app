import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# --- Sayfa Ayarları ---
st.set_page_config(page_title="Echt Nederlands", page_icon="🇳🇱")

st.title("🇳🇱 Hollandaca Dinleme Pratiği")
st.markdown("Gerçek videolarla Hollandaca öğren.")

# --- Google Sheets Bağlantısı ---
# ttl=0 önbelleği kapatır, her tıklamada veriyi taze çeker
conn = st.connection("gsheets", type=GSheetsConnection)

try:
    data = conn.read(ttl=0)
    if data.empty:
        st.error("Veritabanı boş veya okunamadı.")
        st.stop()
except Exception as e:
    st.error(f"Google Sheets bağlantı hatası: {e}")
    st.stop()

# --- Sidebar (Filtreleme) ---
with st.sidebar:
    st.header("Ayarlar")
    # Mevcut seviyeleri veritabanından çekip listele
    seviyeler = sorted(data['seviye'].unique().tolist())
    secilen_seviye = st.selectbox("Seviye Seç:", seviyeler)
    
    # "Soru Getir" butonu buraya daha çok yakışır
    yeni_soru_btn = st.button("Yeni Soru Getir 🎲", type="primary")

# Seçilen seviyeye göre soruları filtrele
filtrelenmis_sorular = data[data['seviye'] == secilen_seviye]

# --- Soru Seçme Mantığı ---
# Butona basıldığında VEYA henüz hiç soru seçilmemişse çalışır
if yeni_soru_btn or 'current_question' not in st.session_state:
    
    if len(filtrelenmis_sorular) == 0:
        st.warning(f"{secilen_seviye} seviyesinde henüz soru yok.")
        st.stop()
        
    # Rastgele bir satır seç
    yeni_soru = filtrelenmis_sorular.sample(1).iloc[0]
    
    # Session State'e kaydet (Sayfa yenilenince kaybolmasın)
    st.session_state['current_question'] = yeni_soru
    
    # Önceki cevabı temizle (Yeni soru geldiği için)
    if 'cevap_verildi' in st.session_state:
        del st.session_state['cevap_verildi']
    
    # Eğer butona basıldıysa sayfayı yenile ki video güncellensin
    if yeni_soru_btn:
        st.rerun()

# --- Soruyu Ekrana Bas ---
if 'current_question' in st.session_state:
    q = st.session_state['current_question']
    
    # 1. Video
    st.video(q['video_url'], start_time=int(q['start_time']))
    
    st.divider()
    
    # 2. Soru
    st.subheader("Boşluğu Doldur:")
    st.markdown(f"### {q['soru_metni']}")
    
    # 3. Cevap Formu (Enter'a basınca çalışsın diye)
    with st.form(key='cevap_formu'):
        kullanici_cevabi = st.text_input("Cevabınız:", key="cevap_input")
        kontrol_btn = st.form_submit_button("Kontrol Et ✅")
    
    # 4. Kontrol Mantığı
    if kontrol_btn:
        dogru = str(q['dogru_cevap']).strip().lower()
        girilen = kullanici_cevabi.strip().lower()
        
        if girilen == dogru:
            st.success("Tebrikler! Doğru cevap. 🎉")
            st.balloons()
            st.session_state['cevap_verildi'] = True
        else:
            st.error("Maalesef yanlış.")
            # İpucu verelim (Kelimenin ilk harfi)
            st.info(f"İpucu: Kelime **{dogru[0].upper()}...** ile başlıyor.")

    # 5. Doğru bilince veya pes edince cevabı göster
    if 'cevap_verildi' in st.session_state:
        st.info(f"Tam Cümle: **{q['soru_metni'].replace('______', q['dogru_cevap'])}**")
