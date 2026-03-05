"""
Sistem Servisi — Dosya, terminal, işlem yönetimi, ekran görüntüsü, pano, dosya arama.
Tüm bağımlılıklar açık kaynak: psutil, pillow, pyperclip.
"""

import fnmatch
import logging
import os
import platform
import subprocess
import webbrowser
from datetime import datetime
from pathlib import Path

import psutil

logger = logging.getLogger(__name__)


# ─── Dosya İşlemleri ──────────────────────────────────────

def dosya_oku(yol: str) -> str:
    """Dosya içeriğini oku."""
    try:
        path = Path(yol).expanduser().resolve()
        if not path.exists():
            return f"❌ Dosya bulunamadı: {path}"
        if not path.is_file():
            return f"❌ Bu bir dosya değil: {path}"
        if path.stat().st_size > 2_000_000:
            return f"⚠️ Dosya çok büyük ({path.stat().st_size / 1024:.0f} KB)"

        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            try:
                content = path.read_text(encoding="latin-1")
            except Exception:
                return f"❌ Dosya okunamadı (binary olabilir): {path}"

        if len(content) > 12000:
            content = content[:12000] + f"\n\n[... kesildi, toplam {len(content)} karakter ...]"

        return f"📄 {path}\n\n{content}"
    except PermissionError:
        return f"🔒 Erişim reddedildi: {yol}"
    except Exception as e:
        return f"❌ Dosya hatası: {str(e)}"


def dosya_yaz(yol: str, icerik: str) -> str:
    """Dosyaya yaz (üzerine yazar, yoksa oluşturur)."""
    try:
        path = Path(yol).expanduser().resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(icerik, encoding="utf-8")
        return f"✅ Yazıldı: {path} ({len(icerik)} karakter)"
    except PermissionError:
        return f"🔒 Yazma izni yok: {yol}"
    except Exception as e:
        return f"❌ Yazma hatası: {str(e)}"


def dosya_listele(yol: str = ".", detayli: bool = False) -> str:
    """Klasör içeriğini listele."""
    try:
        path = Path(yol).expanduser().resolve()
        if not path.exists():
            return f"❌ Klasör bulunamadı: {path}"
        if not path.is_dir():
            return f"❌ Bu bir klasör değil: {path}"

        items = sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
        if not items:
            return f"📁 {path} — boş"

        cikti = f"📁 {path}\n\n"
        sayac = 0
        for item in items:
            if item.name.startswith("."):
                continue
            sayac += 1
            if sayac > 100:
                cikti += f"\n  ... ve daha fazla ({len(list(path.iterdir())) - 100}+ öğe)"
                break

            if item.is_dir():
                cikti += f"  📂 {item.name}/\n"
            else:
                if detayli:
                    boyut = item.stat().st_size
                    if boyut < 1024:
                        b = f"{boyut} B"
                    elif boyut < 1048576:
                        b = f"{boyut/1024:.1f} KB"
                    else:
                        b = f"{boyut/1048576:.1f} MB"
                    cikti += f"  📄 {item.name} ({b})\n"
                else:
                    cikti += f"  📄 {item.name}\n"

        return cikti
    except PermissionError:
        return f"🔒 Erişim reddedildi: {yol}"
    except Exception as e:
        return f"❌ Listeleme hatası: {str(e)}"


def dosya_ara(baslangic_yolu: str, desen: str, icerik_ara: str = None) -> str:
    """Dosya ara — isme göre (glob) ve isteğe bağlı içerik araması."""
    try:
        baslangic = Path(baslangic_yolu).expanduser().resolve()
        if not baslangic.exists():
            return f"❌ Yol bulunamadı: {baslangic}"

        bulunanlar = []
        sayac = 0

        for root, dirs, files in os.walk(baslangic):
            # Gizli ve büyük klasörleri atla
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in (
                "node_modules", "__pycache__", ".git", "venv", ".venv"
            )]

            for fname in files:
                if fnmatch.fnmatch(fname.lower(), desen.lower()):
                    tam_yol = os.path.join(root, fname)

                    # İçerik araması
                    if icerik_ara:
                        try:
                            with open(tam_yol, "r", encoding="utf-8", errors="ignore") as f:
                                content = f.read(100000)
                            if icerik_ara.lower() not in content.lower():
                                continue
                        except Exception:
                            continue

                    bulunanlar.append(tam_yol)
                    sayac += 1
                    if sayac >= 50:
                        break

            if sayac >= 50:
                break

        if not bulunanlar:
            return f"Dosya bulunamadı: desen='{desen}'" + (f", içerik='{icerik_ara}'" if icerik_ara else "")

        cikti = f"🔍 {len(bulunanlar)} dosya bulundu:\n\n"
        for b in bulunanlar:
            cikti += f"  📄 {b}\n"

        return cikti
    except Exception as e:
        return f"❌ Arama hatası: {str(e)}"


# ─── Terminal ─────────────────────────────────────────────

def komut_calistir(komut: str, cwd: str = None, timeout: int = 30) -> str:
    """Shell komutu çalıştır."""
    try:
        tehlikeli = ["rm -rf /", "format C:", "del /s /q C:", ":(){", "mkfs"]
        for t in tehlikeli:
            if t in komut:
                return f"⚠️ Tehlikeli komut engellendi: {komut}"

        result = subprocess.run(
            komut, shell=True, capture_output=True, text=True,
            timeout=timeout, cwd=cwd, env={**os.environ},
        )

        cikti = f"💻 $ {komut}\n"
        if result.stdout:
            out = result.stdout.strip()
            if len(out) > 5000:
                out = out[:5000] + "\n[... kesildi ...]"
            cikti += f"\n{out}\n"
        if result.stderr:
            err = result.stderr.strip()
            if len(err) > 2000:
                err = err[:2000] + "\n[... kesildi ...]"
            cikti += f"\n⚠️ {err}\n"
        cikti += f"\n{'✅ OK' if result.returncode == 0 else f'❌ Çıkış kodu: {result.returncode}'}"
        return cikti

    except subprocess.TimeoutExpired:
        return f"⏱️ Zaman aşımı ({timeout}s): {komut}"
    except Exception as e:
        return f"❌ Komut hatası: {str(e)}"


# ─── Uygulama / URL ──────────────────────────────────────

def uygulama_ac(hedef: str) -> str:
    """URL veya uygulama aç."""
    try:
        if hedef.startswith(("http://", "https://", "www.")):
            webbrowser.open(hedef)
            return f"🌐 Tarayıcıda açıldı: {hedef}"

        sistem = platform.system()
        if sistem == "Windows":
            os.startfile(hedef)
        elif sistem == "Darwin":
            subprocess.Popen(["open", hedef])
        else:
            subprocess.Popen(["xdg-open", hedef])

        return f"✅ Açıldı: {hedef}"
    except Exception as e:
        return f"❌ Açılamadı: {str(e)}"


# ─── Sistem Bilgisi ──────────────────────────────────────

def sistem_bilgisi() -> str:
    """CPU, RAM, disk bilgileri."""
    try:
        cpu = psutil.cpu_percent(interval=1)
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        uptime_s = int(psutil.boot_time())
        from datetime import datetime as dt
        boot = dt.fromtimestamp(uptime_s).strftime("%d.%m.%Y %H:%M")

        return (
            f"💻 Sistem Bilgileri:\n\n"
            f"  🖥️ OS: {platform.system()} {platform.release()}\n"
            f"  🔧 İşlemci: {platform.processor() or 'N/A'}\n"
            f"  ⚡ CPU: %{cpu}\n"
            f"  🧠 RAM: {ram.used / (1024**3):.1f}/{ram.total / (1024**3):.1f} GB (%{ram.percent})\n"
            f"  💾 Disk: {disk.used / (1024**3):.1f}/{disk.total / (1024**3):.1f} GB (%{disk.percent})\n"
            f"  🕐 Açılış: {boot}\n"
            f"  🌐 Hostname: {platform.node()}"
        )
    except Exception as e:
        return f"❌ Sistem bilgisi hatası: {str(e)}"


# ─── İşlem Yönetimi ──────────────────────────────────────

def islem_listele(filtre: str = None) -> str:
    """Çalışan işlemleri listele."""
    try:
        islemler = []
        for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_info"]):
            try:
                info = proc.info
                if filtre and filtre.lower() not in info["name"].lower():
                    continue
                ram_mb = info["memory_info"].rss / (1024 * 1024) if info["memory_info"] else 0
                islemler.append((info["name"], info["pid"], info["cpu_percent"] or 0, ram_mb))
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        # RAM'e göre sırala, en çok kullananlar üstte
        islemler.sort(key=lambda x: x[3], reverse=True)
        islemler = islemler[:30]  # Max 30

        if not islemler:
            return "Eşleşen işlem bulunamadı." if filtre else "İşlem listesi boş."

        cikti = f"⚙️ Çalışan İşlemler{f' (filtre: {filtre})' if filtre else ''}:\n\n"
        for name, pid, cpu, ram in islemler:
            cikti += f"  {name} (PID:{pid}) — CPU:%{cpu:.0f} RAM:{ram:.0f}MB\n"

        return cikti
    except Exception as e:
        return f"❌ İşlem listesi hatası: {str(e)}"


def islem_kapat(islem_adi: str) -> str:
    """İşlem (program) kapat."""
    try:
        kapatilan = 0
        for proc in psutil.process_iter(["name"]):
            try:
                if islem_adi.lower() in proc.info["name"].lower():
                    proc.terminate()
                    kapatilan += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        if kapatilan:
            return f"✅ {kapatilan} '{islem_adi}' işlemi kapatıldı."
        return f"❌ '{islem_adi}' adında çalışan işlem bulunamadı."
    except Exception as e:
        return f"❌ Kapatma hatası: {str(e)}"


# ─── Ekran Görüntüsü ─────────────────────────────────────

def ekran_goruntusu(kayit_yolu: str = None) -> str:
    """Ekran görüntüsü al (Pillow ile)."""
    try:
        from PIL import ImageGrab
    except ImportError:
        return "❌ Ekran görüntüsü alınamadı: Pillow kurulu değil veya bu ortamda desteklenmiyor."

    try:
        if not kayit_yolu:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            desktop = Path.home() / "Desktop"
            if not desktop.exists():
                desktop = Path.home()
            kayit_yolu = str(desktop / f"ekran_{ts}.png")

        img = ImageGrab.grab()
        img.save(kayit_yolu)
        return f"📸 Ekran görüntüsü kaydedildi: {kayit_yolu}"
    except Exception as e:
        return f"❌ Ekran görüntüsü hatası: {str(e)}"


# ─── Pano (Clipboard) ────────────────────────────────────

def panoya_kopyala(metin: str) -> str:
    """Metni panoya kopyala."""
    try:
        import pyperclip
        pyperclip.copy(metin)
        return f"📋 Panoya kopyalandı ({len(metin)} karakter)"
    except Exception:
        # Fallback: platform komutları
        try:
            sistem = platform.system()
            if sistem == "Darwin":
                subprocess.run(["pbcopy"], input=metin.encode(), check=True)
            elif sistem == "Windows":
                subprocess.run(["clip"], input=metin.encode(), check=True)
            else:
                subprocess.run(["xclip", "-selection", "clipboard"], input=metin.encode(), check=True)
            return f"📋 Panoya kopyalandı ({len(metin)} karakter)"
        except Exception as e2:
            return f"❌ Panoya kopyalanamadı: {str(e2)}"


def panodan_oku() -> str:
    """Panodaki metni oku."""
    try:
        import pyperclip
        content = pyperclip.paste()
        if content:
            return f"📋 Panodaki içerik:\n\n{content[:3000]}"
        return "📋 Pano boş."
    except Exception:
        try:
            sistem = platform.system()
            if sistem == "Darwin":
                result = subprocess.run(["pbpaste"], capture_output=True, text=True)
                return f"📋 Pano:\n\n{result.stdout[:3000]}" if result.stdout else "📋 Pano boş."
            elif sistem == "Windows":
                result = subprocess.run(["powershell", "Get-Clipboard"], capture_output=True, text=True)
                return f"📋 Pano:\n\n{result.stdout[:3000]}" if result.stdout else "📋 Pano boş."
        except Exception as e2:
            return f"❌ Pano okunamadı: {str(e2)}"
