import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from youtube_transcript_api import YouTubeTranscriptApi
import yt_dlp
import random
import time

# --- Sayfa Ayarları ---
st.set_page_config(page_title="Echt Nederlands", page_icon="🇳🇱")

# --- Yardımcı Fonksiyon: Youtube Arama (Maskelenmiş) ---
def youtube_ara(query, limit=5):
    """
    yt-dlp kullanarak YouTube'da video arar veya linki çözer.
    YouTube'un bot korumasını aşmak için tarayıcı gibi davranır.
    """
    
    # YouTube'u kandırmak için sahte tarayıcı başlıkları
    ydl_opts = {
        'quiet': True,
        'extract_flat': True, # Sadece listeyi al
        'nocheckcertificate': True,
        'ignoreerrors': True,
        'no_warnings': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    }

    # Eğer kullanıcı direkt link yapıştırdıysa arama yapma, linki çöz
    if query.startswith("http"):
        ydl_opts['default_search'] = 'auto' # Link ise otomatik tanı
    else:
        ydl_opts['default_search'] = f'ytsearch{limit}' # Kelime ise ara

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            # force_generic_extractor=False önemli
            result = ydl.extract_info(query, download=False)
            
            if 'entries' in result:
                # Bir playlist veya arama sonucuysa
                return list(filter(None, result['entries'])) # None olanları temizle
            elif 'id' in result:
                # Tek bir video linkiyse
                return [result]
        except Exception as e:
            st.error(f"YouTube bağlantı hatası: {str(e)}")
    return []

# --- Fonksiyon: Otomatik İçerik Üretici ---
def otomatik_icerik_uret(konu, video_limiti=3, soru_basina_video=3):
    dersler = []
    loglar = []
    
    # 1. Videoları Bul
    loglar.append(f"🔎 '{konu}' taranıyor...")
    sonuclar = youtube_ara(konu, limit=video_limiti)
    
    if not sonuclar:
        loglar.append("❌ YouTube hiçbir sonuç döndürmedi. (IP engeli olabilir)")
        return dersler, loglar
    
    loglar.append(f"✅ {len(sonuclar)} video bulundu. Altyazılar kontrol ediliyor...")

    for video in sonuclar:
        if not video: continue # Boş veri geldiyse geç
        
        vid_id = video.get('id')
        vid_title = video.get('title', 'Başlıksız Video')
        
        try:
            # 2. Altyazı Çekme
            # Listeyi al, hem Hollandaca (nl) hem otomatik (generated) olanlara bak
            transcript_list = YouTubeTranscriptApi.list_transcripts(vid_id)
            
            target_transcript = None
            
            # Öncelik 1: Gerçek Hollandaca Altyazı
            try:
                target_transcript = transcript_list.find_transcript(['nl', 'nl-NL'])
            except:
                # Öncelik 2: Otomatik Üretilmiş Hollandaca
                try:
                    target_transcript = transcript_list.find_generated_transcript(['nl', 'nl-NL'])
                except:
                    loglar.append(f"🔸 Atlandı (Altyazı yok): {vid_title[:20]}...")
                    continue

            full_data = target_transcript.fetch()
            
            # 3. Soru Çıkarma
            bulunan = 0
            kullanilan_cumleler = []
            
            for satir in full_data:
                if bulunan >= soru_basina_video: break
                if satir['start'] > 600: break # İlk 10 dakikaya bak
                
                txt = satir['text'].replace('\n', ' ').strip()
                
                # Gereksiz karakter temizliği
                if "[" in txt or "(" in txt or "♫" in txt: continue
                
                kelimeler = txt.split()
                if len(kelimeler) < 4 or len(kelimeler) > 20: continue
                if txt in kullanilan_cumleler: continue
                
                # Soru yap
                adaylar = [k for k in kelimeler if len(k) > 4]
                if not adaylar: continue
                
                cevap = random.choice(adaylar)
                temiz_cevap = ''.join(e for e in cevap if e.isalnum())
                
                if len(temiz_cevap) < 3: continue 
                
                soru = txt.replace(cevap, "______")
                
                dersler.append({
                    "video_url": f"https://www.youtube.com/watch?v={vid_id}",
                    "start_time": int(satir['start']),
                    "soru_metni": soru,
                    "dogru_cevap": temiz_cevap,
                    "seviye": "Otomatik"
                })
                
                bulunan += 1
                kullanilan_cumleler.append(txt)
            
            if bulunan > 0:
                loglar.append(f"📥 Eklendi ({bulunan} soru): {vid_title[:20]}...")
                
        except Exception:
            continue
            
    return dersler, loglar

# --- Ana Uygulama ---
st.title("🇳🇱 Hollandaca Dinleme Pratiği")
conn = st.connection("gsheets", type=GSheetsConnection)

# --- Admin Paneli ---
with st.sidebar:
    st.divider()
    st.subheader("🕵️ Admin Paneli")
    sifre = st.text_input("Admin Şifresi", type="password")
    
    if sifre == "1234":
        st.success("Yönetici Modu")
        
        st.info("İpucu: Arama çalışmazsa direkt video linki yapıştırabilirsin.")
        arama_konusu = st.text_input("Arama veya Video Linki", "NOS Jeugdjournaal")
        
        col1, col2 = st.columns(2)
        with col1:
            video_sayisi = st.number_input("Taranacak", 1, 10, 3)
        with col2:
            soru_adedi = st.number_input("Soru/Video", 1, 5, 3)
        
        if st.button("İçerik Bul ve Ekle 🚀"):
            with st.status("İşlem yapılıyor...", expanded=True) as status:
                yeni_veri, loglar = otomatik_icerik_uret(arama_konusu, video_sayisi, soru_adedi)
                
                for log in loglar:
                    st.text(log)
                
                if yeni_veri:
                    try:
                        eski_df = conn.read(ttl=0)
                        yeni_df = pd.DataFrame(yeni_veri)
                        sonuc_df = pd.concat([eski_df, yeni_df], ignore_index=True) if not eski_df.empty else yeni_df
                        conn.update(data=sonuc_df)
                        status.update(label="Tamamlandı!", state="complete", expanded=False)
                        st.success(f"✅ {len(yeni_veri)} yeni soru eklendi!")
                        st.balloons()
                    except Exception as e:
                        st.error(f"Kayıt Hatası: {e}")
                else:
                    status.update(label="Başarısız", state="error")
                    st.warning("Video bulunamadı. Lütfen direkt video linki yapıştırarak deneyin.")

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
