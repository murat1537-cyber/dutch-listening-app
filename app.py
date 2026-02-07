import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from youtube_transcript_api import YouTubeTranscriptApi
import yt_dlp
import random
import time

# --- Sayfa Ayarları ---
st.set_page_config(page_title="Echt Nederlands", page_icon="🇳🇱")

# --- Yardımcı Fonksiyon: Youtube Arama (Yeni ve Güçlü) ---
def youtube_ara(query, limit=5):
    """yt-dlp kullanarak YouTube'da video arar."""
    ydl_opts = {
        'quiet': True,
        'extract_flat': True, # Sadece başlıkları al, videoyu indirme
        'default_search': f'ytsearch{limit}', # Kaç video aranacağı
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            result = ydl.extract_info(query, download=False)
            if 'entries' in result:
                return result['entries']
        except Exception as e:
            st.error(f"Arama modülü hatası: {e}")
    return []

# --- Fonksiyon: Otomatik İçerik Üretici ---
def otomatik_icerik_uret(konu, adet):
    dersler = []
    
    # 1. Videoları Ara
    sonuclar = youtube_ara(konu, limit=adet)
    
    if not sonuclar:
        return []

    for video in sonuclar:
        vid_id = video['id']
        vid_title = video.get('title', 'Bilinmeyen Başlık')
        
        # Streamlit loguna yazalım
        print(f"İnceleniyor: {vid_title}")
        
        try:
            # 2. Altyazı çek
            transcript = YouTubeTranscriptApi.get_transcript(vid_id, languages=['nl', 'nl-NL'])
            
            # İlk 2 dakikadaki (120 sn) ve çok kısa olmayan cümleleri bul
            uygunlar = [t for t in transcript if 10 < t['start'] < 120 and len(t['text'].split()) > 4]
            
            if not uygunlar: continue
            
            # Rastgele bir cümle seç
            secilen = random.choice(uygunlar)
            cumle = secilen['text'].replace('\n', ' ')
            
            # 3. Soru yap
            kelimeler = cumle.split()
            # En az 4 harfli kelimelerden aday oluştur
            adaylar = [k for k in kelimeler if len(k) > 3]
            
            if not adaylar: continue
            
            cevap = random.choice(adaylar)
            # Cevaptaki noktalama işaretlerini temizle (örn: "huis." -> "huis")
            temiz_cevap = ''.join(e for e in cevap if e.isalnum())
            
            if len(temiz_cevap) < 2: continue # Çok kısa temiz cevapları atla
            
            soru = cumle.replace(cevap, "______")
            
            dersler.append({
                "video_url": f"https://www.youtube.com/watch?v={vid_id}",
                "start_time": int(secilen['start']),
                "soru_metni": soru,
                "dogru_cevap": temiz_cevap,
                "seviye": "Otomatik"
            })
            
        except Exception:
            # Altyazısı olmayan videoyu sessizce geç
            continue
            
    return dersler

# --- Ana Uygulama Başlangıcı ---
st.title("🇳🇱 Hollandaca Dinleme Pratiği")

# Veritabanı Bağlantısı
conn = st.connection("gsheets", type=GSheetsConnection)

# --- Admin Paneli (Sidebar) ---
with st.sidebar:
    st.divider()
    st.subheader("🕵️ Admin Paneli")
    sifre = st.text_input("Admin Şifresi", type="password")
    
    if sifre == "1234": # Şifreni buradan değiştirebilirsin
        st.success("Giriş Başarılı!")
        
        arama_konusu = st.text_input("Konu (Örn: Dutch stories)", "Dutch A1 listening")
        video_sayisi = st.slider("Aranacak Video Sayısı", 1, 10, 3)
        
        if st.button("İçerik Bul ve Ekle 🚀"):
            with st.spinner(f"'{arama_konusu}' için YouTube taranıyor..."):
                
                # 1. Yeni içerikleri bul
                yeni_veri_listesi = otomatik_icerik_uret(arama_konusu, video_sayisi)
                
                if yeni_veri_listesi:
                    try:
                        # 2. Mevcut verileri oku
                        eski_df = conn.read(ttl=0)
                        yeni_df = pd.DataFrame(yeni_veri_listesi)
                        
                        # 3. Birleştir
                        # Eğer veritabanı boşsa sadece yeniyi, doluysa ikisini birleştir
                        if eski_df.empty:
                            birlesmis_df = yeni_df
                        else:
                            birlesmis_df = pd.concat([eski_df, yeni_df], ignore_index=True)
                        
                        # 4. Kaydet
                        conn.update(data=birlesmis_df)
                        
                        st.success(f"✅ {len(yeni_veri_listesi)} yeni soru başarıyla eklendi!")
                        st.balloons()
                    except Exception as e:
                        st.error(f"Kayıt hatası: {e}. Google Sheet 'Editor' iznini kontrol et.")
                else:
                    st.warning("Bu konuda uygun altyazılı video bulunamadı. Başka bir konu dene (Örn: 'NOS Jeugdjournaal').")

# --- Öğrenci Arayüzü ---
try:
    df = conn.read(ttl=0)
    
    if df.empty:
        st.info("👋 Henüz hiç ders eklenmemiş. Yandaki Admin panelinden ders ekleyin.")
        st.stop()
        
    # 'Soru Getir' butonu
    if st.button("Soru Getir 🎲", type="primary") or 'q' not in st.session_state:
        # Rastgele soru seç
        if len(df) > 0:
            st.session_state['q'] = df.sample(1).iloc[0]
            st.session_state['cevap_goster'] = False # Yeni soruda cevabı gizle
        else:
            st.warning("Veri yok.")
            st.stop()

    if 'q' in st.session_state:
        q = st.session_state['q']
        
        # Video
        st.video(q['video_url'], start_time=int(q['start_time']))
        st.divider()
        
        # Soru Alanı
        st.subheader("Boşluğu Doldur:")
        st.markdown(f"### 🗣️ {q['soru_metni']}")
        
        with st.form("cevap_form"):
            kullanici_cevabi = st.text_input("Duyduğun kelimeyi yaz:")
            col1, col2 = st.columns(2)
            with col1:
                kontrol = st.form_submit_button("Kontrol Et ✅")
            
        if kontrol:
            dogru = str(q['dogru_cevap']).strip().lower()
            girilen = kullanici_cevabi.strip().lower()
            
            if girilen == dogru:
                st.success("🎉 Tebrikler! Çok iyi duydun.")
                st.balloons()
            else:
                st.error("Maalesef yanlış.")
                st.info(f"İpucu: Kelime **{len(dogru)}** harfli.")

        # Cevabı Görme Opsiyonu
        if st.checkbox("Cevabı Göster 👀"):
             st.info(f"Doğru Cevap: **{q['dogru_cevap']}**")

except Exception as e:
    st.error(f"Bir hata oluştu: {e}")
