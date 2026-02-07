import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# --- Sayfa Ayarları ---
st.set_page_config(page_title="Echt Nederlands", page_icon="🇳🇱")

st.title("🇳🇱 Hollandaca Dinleme Pratiği")
st.markdown("Kısa videolarla Hollandaca öğren.")

# --- Veritabanı Bağlantısı ---
conn = st.connection("gsheets", type=GSheetsConnection)

try:
    df = conn.read(ttl=0)
    if df.empty:
        st.error("Veritabanı boş.")
        st.stop()

    # --- Sidebar ---
    with st.sidebar:
        st.header("Seviye Seç")
        mevcut_seviyeler = sorted(df['seviye'].unique().tolist())
        secilen_seviye = st.selectbox("Seviye:", mevcut_seviyeler)
        
        # "Yeni Soru" butonu burada
        if st.button("Yeni Soru Getir 🎲", type="primary"):
            # Rastgele soru seç ve Session State'e at
            filtrelenmis = df[df['seviye'] == secilen_seviye]
            if not filtrelenmis.empty:
                st.session_state['q'] = filtrelenmis.sample(1).iloc[0]
                st.session_state['cevap_acildi'] = False # Cevabı gizle
                st.session_state['kullanici_cevabi'] = "" # Eski cevabı sil
                st.rerun()

    # --- İlk Açılış Kontrolü ---
    if 'q' not in st.session_state:
        st.info("Soldaki menüden 'Yeni Soru Getir' butonuna basarak başla! 👈")
        st.stop()

    # --- Ana Ekran ---
    q = st.session_state['q']

    # 1. Video (Kısa ve öz)
    st.video(q['video_url'], start_time=int(q['start_time']))
    st.caption("Video yüklenmezse sayfayı yenile.")

    st.divider()

    # 2. Soru Alanı
    st.subheader("Boşluğu Doldur:")
    st.markdown(f"### {q['soru_metni']}")

    # 3. Cevap Formu
    with st.form("cevap_kusu"):
        # Kullanıcı cevabını buraya yazar
        girilen = st.text_input("Cevabın:", key="kullanici_cevabi")
        
        # Butonlar yan yana
        c1, c2 = st.columns([1, 1])
        with c1:
            kontrol_et = st.form_submit_button("Kontrol Et ✅")
        with c2:
            # Pes ederse cevabı görme butonu
            pes_et = st.form_submit_button("Cevabı Göster 👀")

    # 4. Sonuç Ekranı (Sadece butona basılınca çalışır)
    if kontrol_et:
        dogru = str(q['dogru_cevap']).strip().lower()
        cevap = girilen.strip().lower()
        
        if cevap == dogru:
            st.success("🎉 Tebrikler! Çok doğru.")
            st.balloons()
            st.session_state['cevap_acildi'] = True
        else:
            st.error("Maalesef yanlış.")
            st.info(f"İpucu: Kelime **{len(dogru)}** harfli.")

    if pes_et or st.session_state.get('cevap_acildi'):
        st.warning(f"Doğru Cevap: **{q['dogru_cevap']}**")

except Exception as e:
    st.error(f"Hata: {e}")
