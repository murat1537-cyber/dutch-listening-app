import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
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

# --- Fonksiyon: Otomatik İçerik Üretici (V3 - Tam Otomatik) ---
def otomatik_icerik_uret(konu, video_limiti=3, soru_basina_video=3):
    dersler = []
    loglar = [] # Ekrana basmak için işlem kaydı
    
    # 1. Videoları Ara
    sonuclar = youtube_ara(konu, limit=video_limiti)
    
    if not sonuclar:
        loglar.append("❌ YouTube araması sonuç vermedi.")
        return dersler, loglar

    loglar.append(f"🔎 '{konu}' için {len(sonuclar)} video bulundu, taranıyor...")

    for video in sonuclar:
        vid_id = video['id']
        vid_title = video.get('title', 'Bilinmeyen Başlık')
        
        try:
            # 2. Altyazı Çekme (EN KAPSAMLI YÖNTEM)
            # list_transcripts tüm dilleri listeler (Otomatik dahil)
            transcript_list = YouTubeTranscriptApi.list_transcripts(vid_id)
            
            target_transcript = None
            
            # Mevcut altyazıları gez ve 'nl' (Dutch) olanı yakala
            # Hem 'nl' (standart) hem 'nl-NL' (Hollanda) kodlarına bakar
            for t in transcript_list:
                if t.language_code.startswith('nl'): 
                    target_transcript = t
                    break
            
            # Eğer Hollandaca bulamazsa, belki video İngilizcedir ama Hollandaca altyazı vardır?
            # Şimdilik sadece sesi Hollandaca olanlara odaklanıyoruz.
            
            if not target_transcript:
                # Son çare: Otomatik üretilenleri zorla dene
                try:
                    target_transcript = transcript_list.find_generated_transcript(['nl', 'nl-NL'])
                except:
                    loglar.append(f"🔸 Atlandı (Altyazı yok): {vid_title[:30]}...")
                    continue

            # Veriyi çek
            full_data = target_transcript.fetch()
            
            # 3. Soru Çıkarma
            bulunan = 0
            kullanilan_cumleler = []
            
            for satir in full_data:
                if bulunan >= soru_basina_video: break
                
                # Çok uzun süreleri atla (10. dakikadan sonrasına bakma)
                if satir['start'] > 600: break
                
                txt = satir['text'].replace('\n', ' ').strip()
                
                # Çok kısa (ünlem vb.) veya çok uzun cümleleri ele
                kelimeler = txt.split()
                if len(kelimeler) < 4 or len(kelimeler) > 20: continue
                
                if txt in kullanilan_cumleler: continue
                
                # [Muziek] veya (Applaus) gibi ses efektlerini ele
                if "[" in txt or "(" in txt: continue

                # Soru yap
                adaylar = [k for k in kelimeler if len(k) > 4] # En az 5 harfli kelime seç
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
                loglar.append(f"✅ Eklendi ({bulunan} soru): {vid_title[:30]}...")
            else:
                loglar.append(f"🔸 Atlandı (Uygun cümle yok): {vid_title[:30]}...")

        except Exception as e:
            loglar.append(f"⚠️ Hata ({vid_title[:15]}...): {str(e)}")
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
        
        arama_konusu = st.text_input("Konu", "NOS Jeugdjournaal")
        col1, col2 = st.columns(2)
        with col1:
            video_sayisi = st.number_input("Taranacak", 1, 10, 3)
        with col2:
            soru_adedi = st.number_input("Soru/Video", 1, 5, 3)
        
        if st.button("İçerik Bul ve Ekle 🚀"):
            with st.status("İşlem yapılıyor...", expanded=True) as status:
                st.write("YouTube taranıyor...")
                yeni_veri, loglar = otomatik_icerik_uret(arama_konusu, video_sayisi, soru_adedi)
                
                st.write("--- İşlem Günlüğü ---")
                for log in loglar:
                    st.text(log)
                
                if yeni_veri:
                    try:
                        eski_df = conn.read(ttl=0)
                        yeni_df = pd.DataFrame(yeni_veri)
                        sonuc_df = pd.concat([eski_df, yeni_df], ignore_index=True) if not eski_df.empty else yeni_df
                        conn.update(data=sonuc_df)
                        status.update(label="Tamamlandı!", state="complete", expanded=False)
                        st.success(f"✅ Toplam {len(yeni_veri)} yeni soru veritabanına eklendi!")
                        st.balloons()
                    except Exception as e:
                        st.error(f"Kayıt Hatası: {e}")
                else:
                    status.update(label="İçerik Bulunamadı", state="error")
                    st.warning("Hiçbir videodan uygun soru çıkarılamadı. Lütfen konuyu değiştirin.")

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
