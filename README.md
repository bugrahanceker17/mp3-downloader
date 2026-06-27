# 🎵 MP3 / 🎬 MP4 Downloader

YouTube'dan reklamsız, hızlı indirici. Tek dosyalık masaüstü uygulaması.

## Kullanım

**En kolay:** `launch.bat` dosyasına çift tıkla.

Veya terminalden:

```powershell
python mp3_downloader.py
```

1. Video veya oynatma listesi linkini yapıştır
2. Kayıt klasörünü seç (Gözat)
3. **Mod** seç → 🎵 Ses (MP3) veya 🎬 Video (MP4)
4. Kalite / format / hız ayarla → **İndir**

## Özellikler

- 🎵/🎬 **Ses veya Video modu** — tek tıkla geçiş
- 🎚️ **Kalite seçimi**
  - Ses: 320 / 256 / 192 / 128 / 96 kbps
  - Video: En iyi / 2160p / 1440p / 1080p / 720p / 480p / 360p
- 🎼 **Format**
  - Ses: mp3, m4a, wav, flac, opus
  - Video: mp4, mkv, webm
- 🐢 **Hız limiti** (MB/s) — bağlantını boğmadan indir
- 🔗 Tek video **ve** oynatma listesi
- 📁 İstediğin klasöre kaydetme (hatırlanır)
- ⚡ Paralel parça indirme (1–32 kanal, ayarlanabilir)
- 📊 Canlı ilerleme, hız ve ETA + iptal butonu
- 🌙 Donmayan koyu tema arayüz

### İnce ayarlar

- 🖼️ Kapak resmi + şarkı/video etiketi gömme
- 📝 Altyazı gömme (video) — dil seçilebilir (örn. `tr,en`)
- 🚫 **SponsorBlock** — sponsor/self-promo kısımlarını atla
- 🔢 Eş zamanlı parça sayısı
- 🍪 Tarayıcı çerezleri (yaş/üye kısıtlı içerik için: chrome/edge/firefox...)
- 🏷️ Dosya adı şablonu (örn. `%(title)s`, `%(uploader)s - %(title)s`)

## Gereksinimler

| Gereksinim | Sürüm | Nasıl kurulur |
|------------|-------|----------------|
| **Python** | 3.8+ (3.12 test edildi) | [python.org](https://www.python.org/downloads/) — kurarken "Add to PATH" işaretle |
| **yt-dlp** | en güncel | `pip install -r requirements.txt` |
| **FFmpeg** | herhangi güncel | `winget install Gyan.FFmpeg` |

> `tkinter` Python ile birlikte gelir, ayrıca kurmaya gerek yok (Windows/standart Python'da hazır).

**Kurulum (kopyala-yapıştır):**

```powershell
# 1) Python paketleri (yt-dlp)
python -m pip install -r requirements.txt

# 2) FFmpeg (ses dönüştürme + video birleştirme için zorunlu)
winget install Gyan.FFmpeg
```

ffmpeg otomatik bulunur: PATH → winget paketleri → uygulama klasörü. PATH'e ekleme yapmaya gerek yok.

> **Neden `requirements.txt`?** Tek Python paketi (`yt-dlp`) olsa da tek komutla kurulum sağlar.
> **FFmpeg neden orada değil?** O bir pip paketi değil, sistem aracıdır; bu yüzden ayrı (winget ile) kurulur.

## Kullanılan teknolojiler

**Harici bağımlılıklar:**

| Araç | Görev | Lisans |
|------|-------|--------|
| [yt-dlp](https://github.com/yt-dlp/yt-dlp) | YouTube'dan akış indirme / format seçimi / SponsorBlock | Unlicense |
| [FFmpeg](https://ffmpeg.org/) | Ses çıkarma, format dönüştürme, video+ses birleştirme, etiket/kapak/altyazı gömme | LGPL/GPL |

**Python standart kütüphanesi** (ekstra kurulum gerekmez):

| Modül | Kullanım |
|-------|----------|
| `tkinter` / `tkinter.ttk` | Grafik arayüz (koyu tema, widget'lar) |
| `threading` | İndirmeyi arka planda çalıştırıp arayüzü dondurmamak |
| `queue` | İş parçacığı → arayüz arası güvenli mesajlaşma |
| `json` | Ayarları kaydet/yükle (`~/.mp3_downloader.json`) |
| `os`, `sys`, `glob`, `shutil` | Dosya yolu işlemleri ve ffmpeg'i otomatik bulma |

> Arayüz için **harici GUI kütüphanesi yok** — sadece Python ile gelen `tkinter`. Tek harici Python paketi: `yt-dlp`.

## Notlar

- Sadece izin verilen / kendi içeriğini indir.
- yt-dlp'yi ara sıra güncelle: `python -m pip install -U yt-dlp`
- Ayarların `~/.mp3_downloader.json` dosyasında saklanır.
