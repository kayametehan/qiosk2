"""
Veritabanı Katmanı - SQLite ile tüm kayıtlar
"""

import sqlite3
from datetime import date, datetime, timedelta
from typing import Optional

from config import DB_PATH


def baglanti():
    """Veritabanı bağlantısı oluştur."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def tablolari_olustur():
    """Tüm tabloları oluştur."""
    conn = baglanti()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS kilo_kayit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tarih TEXT NOT NULL,
            kilo REAL NOT NULL,
            created_at TEXT DEFAULT (datetime('now', 'localtime'))
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS calisma_kayit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tarih TEXT NOT NULL,
            ders TEXT NOT NULL,
            dakika INTEGER NOT NULL,
            created_at TEXT DEFAULT (datetime('now', 'localtime'))
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS gorev_kayit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tarih TEXT NOT NULL,
            gorev TEXT NOT NULL,
            durum TEXT DEFAULT 'bekliyor',
            created_at TEXT DEFAULT (datetime('now', 'localtime'))
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS ogun_kayit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tarih TEXT NOT NULL,
            ogun_tipi TEXT NOT NULL,
            icerik TEXT NOT NULL,
            kalori INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now', 'localtime'))
        )
    """)

    conn.commit()
    conn.close()


# ─── Kilo İşlemleri ──────────────────────────────────────

def kilo_kaydet(kilo: float, tarih: Optional[str] = None) -> dict:
    """Kilo kaydı ekle. Aynı güne kayıt varsa güncelle."""
    if tarih is None:
        tarih = date.today().isoformat()

    conn = baglanti()
    c = conn.cursor()

    # Aynı güne kayıt var mı kontrol et
    c.execute("SELECT id FROM kilo_kayit WHERE tarih = ?", (tarih,))
    mevcut = c.fetchone()

    if mevcut:
        c.execute("UPDATE kilo_kayit SET kilo = ? WHERE tarih = ?", (kilo, tarih))
    else:
        c.execute("INSERT INTO kilo_kayit (tarih, kilo) VALUES (?, ?)", (tarih, kilo))

    conn.commit()
    conn.close()

    return {"tarih": tarih, "kilo": kilo, "guncellendi": mevcut is not None}


def son_kilo() -> Optional[dict]:
    """En son kilo kaydını getir."""
    conn = baglanti()
    c = conn.cursor()
    c.execute("SELECT tarih, kilo FROM kilo_kayit ORDER BY tarih DESC LIMIT 1")
    row = c.fetchone()
    conn.close()

    if row:
        return {"tarih": row["tarih"], "kilo": row["kilo"]}
    return None


def kilo_gecmisi(gun: int = 7) -> list:
    """Son N günün kilo kayıtlarını getir."""
    conn = baglanti()
    c = conn.cursor()
    c.execute(
        "SELECT tarih, kilo FROM kilo_kayit ORDER BY tarih DESC LIMIT ?",
        (gun,),
    )
    rows = c.fetchall()
    conn.close()
    return [{"tarih": r["tarih"], "kilo": r["kilo"]} for r in rows]


# ─── Çalışma İşlemleri ───────────────────────────────────

def calisma_kaydet(ders: str, dakika: int, tarih: Optional[str] = None) -> dict:
    """Çalışma seansı kaydet."""
    if tarih is None:
        tarih = date.today().isoformat()

    conn = baglanti()
    c = conn.cursor()
    c.execute(
        "INSERT INTO calisma_kayit (tarih, ders, dakika) VALUES (?, ?, ?)",
        (tarih, ders.lower(), dakika),
    )
    conn.commit()
    conn.close()

    return {"tarih": tarih, "ders": ders, "dakika": dakika}


def gunluk_calisma(tarih: Optional[str] = None) -> dict:
    """Bugünkü çalışma özetini getir."""
    if tarih is None:
        tarih = date.today().isoformat()

    conn = baglanti()
    c = conn.cursor()
    c.execute(
        "SELECT ders, SUM(dakika) as toplam FROM calisma_kayit WHERE tarih = ? GROUP BY ders",
        (tarih,),
    )
    rows = c.fetchall()
    conn.close()

    sonuc = {}
    for r in rows:
        sonuc[r["ders"]] = r["toplam"]

    return sonuc


def haftalik_calisma() -> dict:
    """Son 7 günün çalışma özetini getir."""
    bugun = date.today()
    hafta_basi = bugun - timedelta(days=6)

    conn = baglanti()
    c = conn.cursor()
    c.execute(
        """SELECT ders, SUM(dakika) as toplam 
           FROM calisma_kayit 
           WHERE tarih >= ? AND tarih <= ? 
           GROUP BY ders""",
        (hafta_basi.isoformat(), bugun.isoformat()),
    )
    rows = c.fetchall()
    conn.close()

    sonuc = {}
    for r in rows:
        sonuc[r["ders"]] = r["toplam"]

    return sonuc


def haftalik_gunluk_detay() -> list:
    """Son 7 günün gün gün çalışma detayını getir."""
    bugun = date.today()
    hafta_basi = bugun - timedelta(days=6)

    conn = baglanti()
    c = conn.cursor()
    c.execute(
        """SELECT tarih, ders, SUM(dakika) as toplam 
           FROM calisma_kayit 
           WHERE tarih >= ? AND tarih <= ? 
           GROUP BY tarih, ders
           ORDER BY tarih""",
        (hafta_basi.isoformat(), bugun.isoformat()),
    )
    rows = c.fetchall()
    conn.close()

    return [{"tarih": r["tarih"], "ders": r["ders"], "toplam": r["toplam"]} for r in rows]


# ─── Görev İşlemleri ─────────────────────────────────────

def gorev_ekle(gorev: str, tarih: Optional[str] = None) -> int:
    """Görev ekle, görev ID'sini döndür."""
    if tarih is None:
        tarih = date.today().isoformat()

    conn = baglanti()
    c = conn.cursor()
    c.execute(
        "INSERT INTO gorev_kayit (tarih, gorev) VALUES (?, ?)",
        (tarih, gorev),
    )
    gorev_id = c.lastrowid
    conn.commit()
    conn.close()

    return gorev_id


def gorev_tamamla(gorev_id: int) -> bool:
    """Görevi tamamlandı olarak işaretle."""
    conn = baglanti()
    c = conn.cursor()
    c.execute(
        "UPDATE gorev_kayit SET durum = 'tamamlandi' WHERE id = ?",
        (gorev_id,),
    )
    degisim = c.rowcount
    conn.commit()
    conn.close()

    return degisim > 0


def gorev_ertele(gorev_id: int) -> bool:
    """Görevi ertelendi olarak işaretle."""
    conn = baglanti()
    c = conn.cursor()
    c.execute(
        "UPDATE gorev_kayit SET durum = 'ertelendi' WHERE id = ?",
        (gorev_id,),
    )
    degisim = c.rowcount
    conn.commit()
    conn.close()

    return degisim > 0


def gunun_gorevleri(tarih: Optional[str] = None) -> list:
    """Bugünkü görevleri getir."""
    if tarih is None:
        tarih = date.today().isoformat()

    conn = baglanti()
    c = conn.cursor()
    c.execute(
        "SELECT id, gorev, durum FROM gorev_kayit WHERE tarih = ? ORDER BY id",
        (tarih,),
    )
    rows = c.fetchall()
    conn.close()

    return [{"id": r["id"], "gorev": r["gorev"], "durum": r["durum"]} for r in rows]


# ─── Öğün İşlemleri ──────────────────────────────────────

def ogun_kaydet(ogun_tipi: str, icerik: str, kalori: int = 0, tarih: Optional[str] = None) -> dict:
    """Öğün kaydı ekle."""
    if tarih is None:
        tarih = date.today().isoformat()

    conn = baglanti()
    c = conn.cursor()
    c.execute(
        "INSERT INTO ogun_kayit (tarih, ogun_tipi, icerik, kalori) VALUES (?, ?, ?, ?)",
        (tarih, ogun_tipi, icerik, kalori),
    )
    conn.commit()
    conn.close()

    return {"tarih": tarih, "ogun_tipi": ogun_tipi, "icerik": icerik, "kalori": kalori}


def gunluk_ogunler(tarih: Optional[str] = None) -> list:
    """Bugünkü öğünleri getir."""
    if tarih is None:
        tarih = date.today().isoformat()

    conn = baglanti()
    c = conn.cursor()
    c.execute(
        "SELECT ogun_tipi, icerik, kalori FROM ogun_kayit WHERE tarih = ? ORDER BY id",
        (tarih,),
    )
    rows = c.fetchall()
    conn.close()

    return [{"ogun_tipi": r["ogun_tipi"], "icerik": r["icerik"], "kalori": r["kalori"]} for r in rows]


# ─── İstatistikler ───────────────────────────────────────

def genel_istatistik() -> dict:
    """Genel istatistikleri getir."""
    conn = baglanti()
    c = conn.cursor()

    # Toplam çalışma
    c.execute("SELECT SUM(dakika) as toplam FROM calisma_kayit")
    toplam_calisma = c.fetchone()["toplam"] or 0

    # Bu haftaki çalışma
    bugun = date.today()
    hafta_basi = bugun - timedelta(days=6)
    c.execute(
        "SELECT SUM(dakika) as toplam FROM calisma_kayit WHERE tarih >= ?",
        (hafta_basi.isoformat(),),
    )
    hafta_calisma = c.fetchone()["toplam"] or 0

    # Kilo değişimi
    c.execute("SELECT kilo FROM kilo_kayit ORDER BY tarih ASC LIMIT 1")
    ilk_kilo_row = c.fetchone()
    ilk_kilo = ilk_kilo_row["kilo"] if ilk_kilo_row else None

    c.execute("SELECT kilo FROM kilo_kayit ORDER BY tarih DESC LIMIT 1")
    son_kilo_row = c.fetchone()
    son_kilo_val = son_kilo_row["kilo"] if son_kilo_row else None

    # Tamamlanan görev sayısı
    c.execute("SELECT COUNT(*) as sayi FROM gorev_kayit WHERE durum = 'tamamlandi'")
    tamamlanan = c.fetchone()["sayi"]

    c.execute("SELECT COUNT(*) as sayi FROM gorev_kayit")
    toplam_gorev = c.fetchone()["sayi"]

    conn.close()

    return {
        "toplam_calisma_dk": toplam_calisma,
        "hafta_calisma_dk": hafta_calisma,
        "ilk_kilo": ilk_kilo,
        "son_kilo": son_kilo_val,
        "tamamlanan_gorev": tamamlanan,
        "toplam_gorev": toplam_gorev,
    }
