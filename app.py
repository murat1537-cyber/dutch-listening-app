import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from youtube_transcript_api import YouTubeTranscriptApi
from youtubesearchpython import VideosSearch
import random
import time

# --- Sayfa Ayarları ---
st.set_page_config(page_title="Echt Nederlands", page_icon="🇳🇱")

# --- Fonksiyon: Otomatik Video Bulucu (Hunter) ---
def otomatik_icerik_uret(konu, adet):
    dersler = []
    try:
        search = VideosSearch(konu, limit=adet)
        results = search.result()['result']
        
        for video in results:
            vid_id = video['id']
            try:
                # Altyazı çek
                transcript = YouTubeTranscriptApi.get_transcript(vid_id, languages=['nl', 'nl-NL'])
                # İlk 2 dakikadaki uygun cümleleri bul
                uygunlar = [t for t in transcript if 10 < t['start'] < 120 and len(t['text'].split()) > 4]
                
                if not uygunlar: continue
                
                secilen = random.choice(uygunlar)
                cumle = secilen['text'].replace('\n', ' ')
                
                # Soru yap
                kelimeler = cumle.split()
                adaylar = [k for k in kelimeler if len(k) > 3]
                if not adaylar: continue
                
                cevap = random.choice(adaylar)
                temiz_cevap = ''.join(e for e in cevap if e.isalnum())
                soru = cumle.replace(cevap, "______")
                
                dersler.append({
                    "video_url": f"https://www.youtube.com/watch?v={vid_id}",
                    "start_time": int(secilen['start']),
                    "soru_metni": soru,
                    "dogru_cevap": temiz_cevap,
                    "seviye": "Otomatik"
                })
            except:
                continue
    except Exception as e:
        st.error(f"Arama hatası: {e}")
        
    return dersler

# --- Ana Uygulama ---
st.title("🇳🇱 Hollandaca Dinleme Pratiği")

# Bağlantı
conn = st.connection("gsheets", type=GSheetsConnection)

# --- Admin Paneli (Sidebar'da Gizli) ---
with st.sidebar:
    st.divider()
    st.subheader("🕵️ Admin Paneli")
    sifre = st.text_input("Admin Şifresi", type="password")
    
    # Şifreyi '1234' olarak belirledim, değiştirebilirsin
    if sifre == "1234":
        st.success("Giriş Başarılı!")
        
        arama_konusu = st.text_input("Konu (Örn: Dutch stories)", "Dutch A1 listening")
        video_sayisi = st.slider("Kaç video aransın?", 1, 5, 3)
        
        if st.button("İçerik Bul ve Ekle 🚀"):
            with st.spinner("YouTube taranıyor... Bu işlem 1-2 dakika sürebilir."):
                # 1. Yeni verileri bul
                yeni_veri_listesi = otomatik_icerik_uret(arama_konusu, video_sayisi)
                
                if yeni_veri_listesi:
                    # 2. Mevcut verileri oku
                    eski_df = conn.read(ttl=0)
                    yeni_df = pd.DataFrame(yeni_veri_listesi)
                    
                    # 3. Birleştir
                    birlesmis_df = pd.concat([eski_df, yeni_df], ignore_index=True)
                    
                    # 4. Google Sheets'i Güncelle (Yaz)
                    conn.update(data=birlesmis_df)
                    
                    st.success(f"{len(yeni_veri_listesi)} yeni ders veritabanına eklendi!")
                    st.balloons()
                else:
                    st.warning("Uygun video bulunamadı, başka bir konu dene.")

# --- Öğrenci Arayüzü (Normal Ekran) ---
try:
    # Veriyi çek
    df = conn.read(ttl=0)
    if df.empty:
        st.info("Henüz ders yok. Admin panelinden ekleyin.")
        st.stop()
        
    # Rastgele Soru Getir
    if st.button("Soru Getir 🎲", type="primary"):
        row = df.sample(1).iloc[0]
        st.session_state['q'] = row
        st.rerun()

    if 'q' in st.session_state:
        q = st.session_state['q']
        st.video(q['video_url'], start_time=int(q['start_time']))
        st.write(f"**Soru:** {q['soru_metni']}")
        
        with st.form("cevap"):
            cvp = st.text_input("Cevap")
            btn = st.form_submit_button("Kontrol")
            if btn:
                if cvp.lower().strip() == str(q['dogru_cevap']).lower().strip():
                    st.success("Doğru!")
                else:
                    st.error("Yanlış!")
                    st.info(f"Cevap: {q['dogru_cevap']}")

except Exception as e:
    st.error("Veritabanı okunurken hata oluştu. Lütfen Google Sheet paylaşım ayarının 'Editor' olduğundan emin olun.")
