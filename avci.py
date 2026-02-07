import pandas as pd
from youtube_transcript_api import YouTubeTranscriptApi
from youtubesearchpython import VideosSearch
import random
import time

def video_bul_ve_isle(arama_terimi="Dutch listening practice A1", video_sayisi=5):
    print(f"🔍 '{arama_terimi}' için YouTube taranıyor...")
    
    # 1. YouTube'da Arama Yap
    videos_search = VideosSearch(arama_terimi, limit=video_sayisi)
    sonuclar = videos_search.result()['result']
    
    yeni_dersler = []

    for video in sonuclar:
        video_id = video['id']
        video_title = video['title']
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        
        print(f"  ➡️ İşleniyor: {video_title[:30]}...")
        
        try:
            # 2. Altyazıyı Çek (Hollandaca)
            # Önce Hollandaca (nl), yoksa otomatik üretilmiş (nl-NL) altyazıyı dener
            transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['nl', 'nl-NL'])
            
            # 3. Uygun Cümle Bul (Rastgele bir yerinden değil, başlardan seçelim)
            # İlk 60 saniyedeki cümlelere odaklanalım ki kullanıcı videoyu çok aramasın
            uygun_satirlar = [t for t in transcript if 10 < t['start'] < 120 and len(t['text'].split()) > 4]
            
            if not uygun_satirlar:
                print("     ❌ Uygun uzunlukta cümle bulunamadı.")
                continue

            secilen = random.choice(uygun_satirlar)
            cumle = secilen['text'].replace('\n', ' ')
            start_time = int(secilen['start'])
            
            # 4. Soru Oluştur (Boşluk Doldurma)
            kelimeler = cumle.split()
            # En az 4 harfli bir kelime seç
            adaylar = [k for k in kelimeler if len(k) > 3]
            
            if not adaylar:
                gizli_kelime = kelimeler[-1] # Son kelimeyi al
            else:
                gizli_kelime = random.choice(adaylar)
            
            # Noktalama işaretlerini temizle
            temiz_cevap = ''.join(e for e in gizli_kelime if e.isalnum())
            soru_metni = cumle.replace(gizli_kelime, "______")
            
            # 5. Listeye Ekle
            yeni_dersler.append({
                "video_url": video_url,
                "start_time": start_time,
                "soru_metni": soru_metni,
                "dogru_cevap": temiz_cevap,
                "seviye": "A1" if "A1" in arama_terimi else "A2"
            })
            
            print(f"     ✅ Soru üretildi: {temiz_cevap}")
            time.sleep(1) # YouTube'u kızdırmamak için bekleme

        except Exception as e:
            print(f"     ⚠️ Altyazı hatası: {e}")
            continue

    return yeni_dersler

# --- Ana Program ---
if __name__ == "__main__":
    # Hangi konuda video istiyorsan buraya yaz
    konular = ["Dutch stories A1", "NOS Jeugdjournaal", "Dutch listening A2"]
    
    tum_dersler = []
    for konu in konular:
        dersler = video_bul_ve_isle(konu, video_sayisi=3)
        tum_dersler.extend(dersler)
    
    # CSV Dosyasına Kaydet
    if tum_dersler:
        df = pd.DataFrame(tum_dersler)
        dosya_adi = "yeni_dersler.csv"
        df.to_csv(dosya_adi, index=False)
        print(f"\n🎉 İşlem tamam! {len(tum_dersler)} yeni ders '{dosya_adi}' dosyasına kaydedildi.")
        print("Şimdi bu dosyanın içeriğini kopyalayıp Google Sheets'e yapıştırabilirsin.")
    else:
        print("\n😔 Maalesef uygun video bulunamadı.")