import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from youtube_transcript_api import YouTubeTranscriptApi
import yt_dlp
import random
import time

# --- Sayfa Ayarları ---
st.set_page_config(page_title="Echt Nederlands", page_icon="🇳🇱")

# --- Yardımcı Fonksiyon: Youtube Arama ---
def youtube_ara(query, limit=5):
    """yt-dlp kullanarak YouTube'da video arar."""
    ydl_opts = {
        'quiet': True,
        'extract_flat': True,
        'default_search': f'ytsearch{limit}',
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            result = ydl.extract_info(query, download=False)
            if 'entries' in result:
                return result['entries']
        except Exception as e:
            st.error(f"Arama modülü hatası: {e}")
    return []

# --- Fonksiyon: Otomatik İçerik Üretici (Gelişmiş) ---
def otomatik_icerik_uret(konu, video_limiti=3, soru_basina_video=3):
    dersler = []
    
    # 1. Videoları Ara
    sonuclar = youtube_ara(konu, limit=video_limiti)
    
    if not sonuclar:
        return []

    for video in sonuclar:
        vid_id = video['id']
        vid_title = video.get('title', 'Bilinmeyen Başlık')
        
        print(f"İnceleniyor: {vid_title}")
        
        try:
            # 2. Altyazı Çekme (Daha Esnek)
            # Hem elle yazılmış (nl) hem otomatik (nl-NL) altyazıları dener
            # List_transcripts kullanarak en uygununu bulmaya çalışırız
            transcript_list = YouTubeTranscriptApi.list_transcripts(vid_id)
            
            # Hollandaca var mı diye bak, yoksa otomatiği al
            try:
                transcript = transcript_list.find_transcript(['nl', 'nl-NL'])
            except:
                # Eğer Hollandaca yoksa, ama video varsa, bazen otomatik çeviri yapılabilir
                # Şimdilik sadece doğrudan Hollandaca olanları alıyoruz (kalite için)
                continue

            full_data = transcript.fetch()
            
            # 3. Aynı Videodan 3 Soru Çıkarma Döngüsü
            bulunan_soru_sayisi = 0
            kullanilan_cumleler = [] # Aynı cümleyi tekrar sormamak için
            
            # Videonun başından sonuna kadar tara
            for satir in full_data:
                # 3 soru kotası dolduysa bu videodan çık
                if bulunan_soru_sayisi >= soru_basina_video:
                    break
                
                # Sadece ilk 5 dakikadaki kısımları al (Kullanıcı videoda kaybolmasın)
                if satir['start'] > 300: 
                    break
                
                # Çok kısa cümleleri atla
                if len(satir['text'].split()) < 4:
                    continue
                    
                cumle = satir['text'].replace('\n', ' ').strip()
                
                # Bu cümleyi daha önce kullandıysak atla
                if cumle in kullanilan_cumleler:
                    continue
                
                # Soru yap
                kelimeler = cumle.split()
                adaylar = [k for k in kelimeler if len(k) > 3]
                
                if not adaylar: continue
                
                # Kelime seçimi (random)
                cevap = random.choice(adaylar)
                temiz_cevap = ''.join(e for e in cevap if e.isalnum())
                
                if len(temiz_cevap) < 3: continue 
                
                soru = cumle.replace(cevap, "______")
                
                # Listeye Ekle
                dersler.append({
                    "video_url": f"https://www.youtube.com/watch?v={vid_id}",
                    "start_time": int(satir['start']),
                    "soru_metni": soru,
                    "dogru_cevap": temiz_cevap,
                    "seviye": "Otomatik"
                })
                
                # Kayıtları güncelle
                bulunan_soru_sayisi += 1
                kullanilan_cumleler.append(cumle)
            
        except Exception as e:
            # Altyazı yoksa veya hata varsa geç
            continue
            
    return dersler

# --- Ana Uygulama ---
st.title("🇳🇱 Hollandaca Dinleme Pratiği")
conn = st.connection("gsheets", type=GSheetsConnection)

# --- Admin Paneli ---
with st.sidebar:
    st.divider()
    st.subheader("🕵️ Admin Paneli")
    sifre = st.text_input("Admin Şifresi", type="password")
    
    if sifre == "1234":
        st.success("Yönetici Modu Açık")
        
        arama_konusu = st.text_input("Konu", "Dutch vlog")
        col1, col2 = st.columns(2)
        with col1:
            video_sayisi = st.number_input("Taranacak Video", min_value=1, value=3)
        with col2:
            soru_adedi = st.number_input("Video Başına Soru", min_value=1, value=3)
        
        if st.button("İçerik Bul ve Ekle 🚀"):
            with st.spinner(f"YouTube taranıyor... Her videodan {soru_adedi} soru çıkarılacak."):
                yeni_veri = otomatik_icerik_uret(arama_konusu, video_sayisi, soru_adedi)
                
                if yeni_veri:
                    try:
                        eski_df = conn.read(ttl=0)
                        yeni_df = pd.DataFrame(yeni_veri)
                        if eski_df.empty:
                            sonuc_df = yeni_df
                        else:
                            sonuc_df = pd.concat([eski_df, yeni_df], ignore_index=True)
                        
                        conn.update(data=sonuc_df)
                        st.success(f"✅ Toplam {len(yeni_veri)} yeni soru eklendi!")
                        st.balloons()
                    except Exception as e:
                        st.error(f"Kayıt Hatası: {e}")
                else:
                    st.warning("Video bulundu ama uygun altyazı çekilemedi. 'Dutch vlogs', 'NOS', 'NPO Start' gibi terimler deneyin.")

# --- Öğrenci Arayüzü ---
try:
    df = conn.read(ttl=0)
    
    if df.empty:
        st.info("👋 Ders yok. Admin panelinden ekleyin.")
        st.stop()
        
    if st.button("Soru Getir 🎲", type="primary") or 'q' not in st.session_state:
        st.session_state['q'] = df.sample(1).iloc[0]
        st.session_state['cevap_goster'] = False 

    if 'q' in st.session_state:
        q = st.session_state['q']
        st.video(q['video_url'], start_time=int(q['start_time']))
        st.divider()
        st.markdown(f"### 🗣️ {q['soru_metni']}")
        
        with st.form("cevap_form"):
            kullanici_cevabi = st.text_input("Cevap:")
            kontrol = st.form_submit_button("Kontrol Et ✅")
            
        if kontrol:
            dogru = str(q['dogru_cevap']).strip().lower()
            girilen = kullanici_cevabi.strip().lower()
            if girilen == dogru:
                st.success("Doğru!")
                st.balloons()
            else:
                st.error("Yanlış.")
                st.info(f"İpucu: {len(dogru)} harfli.")
                
        if st.checkbox("Cevabı Gör"):
             st.info(f"Cevap: **{q['dogru_cevap']}**")

except Exception as e:
    st.error(f"Hata: {e}")
