import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# --- Sayfa Ayarları ---
st.set_page_config(page_title="Echt Nederlands", page_icon="🇳🇱")

st.title("🇳🇱 Hollandaca Dinleme Pratiği")
st.markdown("Seviyeni seç, videoyu izle ve boşluğu doldur!")

# --- Veritabanı Bağlantısı ---
conn = st.connection("gsheets", type=GSheetsConnection)

try:
    # Veriyi çek (ttl=0: Her seferinde taze veri al)
    df = conn.read(ttl=0)
    
    if df.empty:
        st.error("Veritabanı boş. Lütfen Google Sheets'e veri ekleyin.")
        st.stop()

    # --- Sidebar (Seviye Seçimi) ---
    with st.sidebar:
        st.header("⚙️ Ayarlar")
        
        # Veritabanındaki mevcut seviyeleri bul
        mevcut_seviyeler = sorted(df['seviye'].unique().tolist())
        secilen_seviye = st.selectbox("Hangi seviyede çalışmak istiyorsun?", mevcut_seviyeler)
        
        st.divider()
        st.info("Bu uygulama Google Sheets veritabanı ile çalışır.")

    # --- Soru Seçme Mantığı ---
    # Sadece seçilen seviyedeki soruları filtrele
    filtrelenmis_df = df[df['seviye'] == secilen_seviye]
    
    if filtrelenmis_df.empty:
        st.warning(f"{secilen_seviye} seviyesinde henüz soru yok.")
        st.stop()

    # 'Soru Getir' butonu veya ilk açılış
    if st.button("Yeni Soru Getir 🎲", type="primary") or 'q' not in st.session_state:
        # Rastgele bir satır seç
        st.session_state['q'] = filtrelenmis_df.sample(1).iloc[0]
        st.session_state['cevap_goster'] = False # Cevabı gizle

    # --- Soruyu Ekrana Bas ---
    if 'q' in st.session_state:
        q = st.session_state['q']
        
        # Video Oynatıcı
        st.video(q['video_url'], start_time=int(q['start_time']))
        
        st.divider()
        
        # Soru Kartı
        st.subheader("👂 Duyduğunu Yaz")
        st.markdown(f"### {q['soru_metni']}")
        
        # Cevap Formu
        with st.form("cevap_form"):
            col1, col2 = st.columns([3, 1])
            with col1:
                kullanici_cevabi = st.text_input("Boşluğa ne gelmeli?", key="cevap_input")
            with col2:
                # Butonu biraz aşağı hizalamak için boşluk
                st.write("") 
                st.write("")
                kontrol_btn = st.form_submit_button("Kontrol Et ✅")
            
        # Doğrulama Mantığı
        if kontrol_btn:
            dogru = str(q['dogru_cevap']).strip().lower()
            girilen = kullanici_cevabi.strip().lower()
            
            if girilen == dogru:
                st.success("🎉 Harika! Doğru cevap.")
                st.balloons()
            else:
                st.error("Maalesef yanlış.")
                st.info(f"İpucu: Kelime **{len(dogru)}** harfli ve **'{dogru[0].upper()}...'** ile başlıyor.")

        # Cevabı Göster Butonu (Checkbox yerine buton daha şık)
        if st.expander("Cevabı Göster 👀"):
             st.info(f"Doğru Cevap: **{q['dogru_cevap']}**")

except Exception as e:
    st.error(f"Bağlantı Hatası: {e}")
    st.warning("Google Sheet dosyanızın 'Anyone with link' ve 'Viewer' modunda olduğundan emin olun.")
