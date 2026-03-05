"""
Veritabanı Katmanı — SQLite, güvenli bağlantı yönetimi (context manager).
Tablolar: kilo, çalışma, görev, öğün, sohbet geçmişi, deneme sınavı, kullanıcı profili.
"""

import json
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from typing import Optional

from config import DB_PATH


@contextmanager
def baglanti():
    """Güvenli veritabanı bağlantısı — otomatik commit/rollback/close."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def tablolari_olustur():
    """Tüm tabloları oluştur."""
    with baglanti() as conn:
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

        # ─── Konuşma Hafızası ─────────────────────────
        c.execute("""
            CREATE TABLE IF NOT EXISTS sohbet_gecmisi (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT NOT NULL,
                content TEXT,
                tool_calls_json TEXT,
                tool_call_id TEXT,
                created_at TEXT DEFAULT (datetime('now', 'localtime'))
            )
        """)

        # ─── Deneme Sınavı Skorları ───────────────────
        c.execute("""
            CREATE TABLE IF NOT EXISTS deneme_sinav (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tarih TEXT NOT NULL,
                sinav_turu TEXT NOT NULL,
                bolum TEXT,
                puan INTEGER NOT NULL,
                toplam INTEGER DEFAULT 0,
                notlar TEXT,
                created_at TEXT DEFAULT (datetime('now', 'localtime'))
            )
        """)

        # ─── Kullanıcı Profili (onboarding) ───────────
        c.execute("""
            CREATE TABLE IF NOT EXISTS kullanici_profil (
                anahtar TEXT PRIMARY KEY,
                deger TEXT NOT NULL,
                updated_at TEXT DEFAULT (datetime('now', 'localtime'))
            )
        """)


# ═══════════════════════════════════════════════════════════
# KİLO İŞLEMLERİ
# ═══════════════════════════════════════════════════════════

def kilo_kaydet(kilo: float, tarih: Optional[str] = None) -> dict:
    """Kilo kaydı ekle. Aynı güne kayıt varsa güncelle."""
    if tarih is None:
        tarih = date.today().isoformat()
    with baglanti() as conn:
        c = conn.cursor()
        c.execute("SELECT id FROM kilo_kayit WHERE tarih = ?", (tarih,))
        mevcut = c.fetchone()
        if mevcut:
            c.execute("UPDATE kilo_kayit SET kilo = ? WHERE tarih = ?", (kilo, tarih))
        else:
            c.execute("INSERT INTO kilo_kayit (tarih, kilo) VALUES (?, ?)", (tarih, kilo))
    return {"tarih": tarih, "kilo": kilo, "guncellendi": mevcut is not None}


def son_kilo() -> Optional[dict]:
    """En son kilo kaydını getir."""
    with baglanti() as conn:
        c = conn.cursor()
        c.execute("SELECT tarih, kilo FROM kilo_kayit ORDER BY tarih DESC LIMIT 1")
        row = c.fetchone()
    return {"tarih": row["tarih"], "kilo": row["kilo"]} if row else None


def kilo_gecmisi(gun: int = 7) -> list:
    """Son N günün kilo kayıtlarını getir."""
    with baglanti() as conn:
        c = conn.cursor()
        c.execute("SELECT tarih, kilo FROM kilo_kayit ORDER BY tarih DESC LIMIT ?", (gun,))
        rows = c.fetchall()
    return [{"tarih": r["tarih"], "kilo": r["kilo"]} for r in rows]


# ═══════════════════════════════════════════════════════════
# ÇALIŞMA İŞLEMLERİ
# ═══════════════════════════════════════════════════════════

def calisma_kaydet(ders: str, dakika: int, tarih: Optional[str] = None) -> dict:
    """Çalışma seansı kaydet."""
    if tarih is None:
        tarih = date.today().isoformat()
    with baglanti() as conn:
        c = conn.cursor()
        c.execute("INSERT INTO calisma_kayit (tarih, ders, dakika) VALUES (?, ?, ?)",
                  (tarih, ders.lower(), dakika))
    return {"tarih": tarih, "ders": ders, "dakika": dakika}


def gunluk_calisma(tarih: Optional[str] = None) -> dict:
    """Bugünkü çalışma özetini getir."""
    if tarih is None:
        tarih = date.today().isoformat()
    with baglanti() as conn:
        c = conn.cursor()
        c.execute("SELECT ders, SUM(dakika) as toplam FROM calisma_kayit WHERE tarih = ? GROUP BY ders", (tarih,))
        rows = c.fetchall()
    return {r["ders"]: r["toplam"] for r in rows}


def haftalik_calisma() -> dict:
    """Son 7 günün çalışma özetini getir."""
    bugun = date.today()
    hafta_basi = bugun - timedelta(days=6)
    with baglanti() as conn:
        c = conn.cursor()
        c.execute("""SELECT ders, SUM(dakika) as toplam FROM calisma_kayit
                     WHERE tarih >= ? AND tarih <= ? GROUP BY ders""",
                  (hafta_basi.isoformat(), bugun.isoformat()))
        rows = c.fetchall()
    return {r["ders"]: r["toplam"] for r in rows}


def haftalik_gunluk_detay() -> list:
    """Son 7 günün gün gün çalışma detayını getir."""
    bugun = date.today()
    hafta_basi = bugun - timedelta(days=6)
    with baglanti() as conn:
        c = conn.cursor()
        c.execute("""SELECT tarih, ders, SUM(dakika) as toplam FROM calisma_kayit
                     WHERE tarih >= ? AND tarih <= ?
                     GROUP BY tarih, ders ORDER BY tarih""",
                  (hafta_basi.isoformat(), bugun.isoformat()))
        rows = c.fetchall()
    return [{"tarih": r["tarih"], "ders": r["ders"], "toplam": r["toplam"]} for r in rows]


# ═══════════════════════════════════════════════════════════
# GÖREV İŞLEMLERİ
# ═══════════════════════════════════════════════════════════

def gorev_ekle(gorev: str, tarih: Optional[str] = None) -> int:
    """Görev ekle, görev ID'sini döndür."""
    if tarih is None:
        tarih = date.today().isoformat()
    with baglanti() as conn:
        c = conn.cursor()
        c.execute("INSERT INTO gorev_kayit (tarih, gorev) VALUES (?, ?)", (tarih, gorev))
        gorev_id = c.lastrowid
    return gorev_id


def gorev_tamamla(gorev_id: int) -> bool:
    """Görevi tamamlandı olarak işaretle."""
    with baglanti() as conn:
        c = conn.cursor()
        c.execute("UPDATE gorev_kayit SET durum = 'tamamlandi' WHERE id = ?", (gorev_id,))
        return c.rowcount > 0


def gorev_ertele(gorev_id: int) -> bool:
    """Görevi ertelendi olarak işaretle."""
    with baglanti() as conn:
        c = conn.cursor()
        c.execute("UPDATE gorev_kayit SET durum = 'ertelendi' WHERE id = ?", (gorev_id,))
        return c.rowcount > 0


def gunun_gorevleri(tarih: Optional[str] = None) -> list:
    """Bugünkü görevleri getir."""
    if tarih is None:
        tarih = date.today().isoformat()
    with baglanti() as conn:
        c = conn.cursor()
        c.execute("SELECT id, gorev, durum FROM gorev_kayit WHERE tarih = ? ORDER BY id", (tarih,))
        rows = c.fetchall()
    return [{"id": r["id"], "gorev": r["gorev"], "durum": r["durum"]} for r in rows]


# ═══════════════════════════════════════════════════════════
# ÖĞÜN İŞLEMLERİ
# ═══════════════════════════════════════════════════════════

def ogun_kaydet(ogun_tipi: str, icerik: str, kalori: int = 0, tarih: Optional[str] = None) -> dict:
    """Öğün kaydı ekle."""
    if tarih is None:
        tarih = date.today().isoformat()
    with baglanti() as conn:
        c = conn.cursor()
        c.execute("INSERT INTO ogun_kayit (tarih, ogun_tipi, icerik, kalori) VALUES (?, ?, ?, ?)",
                  (tarih, ogun_tipi, icerik, kalori))
    return {"tarih": tarih, "ogun_tipi": ogun_tipi, "icerik": icerik, "kalori": kalori}


def gunluk_ogunler(tarih: Optional[str] = None) -> list:
    """Bugünkü öğünleri getir."""
    if tarih is None:
        tarih = date.today().isoformat()
    with baglanti() as conn:
        c = conn.cursor()
        c.execute("SELECT ogun_tipi, icerik, kalori FROM ogun_kayit WHERE tarih = ? ORDER BY id", (tarih,))
        rows = c.fetchall()
    return [{"ogun_tipi": r["ogun_tipi"], "icerik": r["icerik"], "kalori": r["kalori"]} for r in rows]


def gunluk_kalori(tarih: Optional[str] = None) -> int:
    """Bugünkü toplam kalori."""
    if tarih is None:
        tarih = date.today().isoformat()
    with baglanti() as conn:
        c = conn.cursor()
        c.execute("SELECT SUM(kalori) as toplam FROM ogun_kayit WHERE tarih = ?", (tarih,))
        row = c.fetchone()
    return row["toplam"] or 0


# ═══════════════════════════════════════════════════════════
# SOHBET GEÇMİŞİ (KONUŞMA HAFIZASI)
# ═══════════════════════════════════════════════════════════

def sohbet_kaydet(role: str, content: Optional[str] = None,
                  tool_calls_json: Optional[str] = None,
                  tool_call_id: Optional[str] = None):
    """Sohbet mesajını kaydet."""
    with baglanti() as conn:
        c = conn.cursor()
        c.execute("""INSERT INTO sohbet_gecmisi (role, content, tool_calls_json, tool_call_id)
                     VALUES (?, ?, ?, ?)""",
                  (role, content, tool_calls_json, tool_call_id))


def sohbet_gecmisi_getir(limit: int = 30) -> list:
    """Son N sohbet mesajını getir (AI'ya context olarak verilecek)."""
    with baglanti() as conn:
        c = conn.cursor()
        c.execute("""SELECT role, content, tool_calls_json, tool_call_id
                     FROM sohbet_gecmisi ORDER BY id DESC LIMIT ?""", (limit,))
        rows = c.fetchall()

    # Ters çevir (eski → yeni sırada)
    mesajlar = []
    for r in reversed(rows):
        msg = {"role": r["role"]}
        if r["content"]:
            msg["content"] = r["content"]
        if r["tool_calls_json"]:
            try:
                msg["tool_calls"] = json.loads(r["tool_calls_json"])
            except json.JSONDecodeError:
                pass
        if r["tool_call_id"]:
            msg["tool_call_id"] = r["tool_call_id"]
        mesajlar.append(msg)

    return mesajlar


def sohbet_temizle():
    """Sohbet geçmişini temizle."""
    with baglanti() as conn:
        c = conn.cursor()
        c.execute("DELETE FROM sohbet_gecmisi")


# ═══════════════════════════════════════════════════════════
# DENEME SINAVI SKORLARI
# ═══════════════════════════════════════════════════════════

def deneme_kaydet(sinav_turu: str, puan: int, bolum: str = None,
                  toplam: int = 0, notlar: str = None, tarih: Optional[str] = None) -> dict:
    """Deneme sınavı sonucunu kaydet."""
    if tarih is None:
        tarih = date.today().isoformat()
    with baglanti() as conn:
        c = conn.cursor()
        c.execute("""INSERT INTO deneme_sinav (tarih, sinav_turu, bolum, puan, toplam, notlar)
                     VALUES (?, ?, ?, ?, ?, ?)""",
                  (tarih, sinav_turu.lower(), bolum, puan, toplam, notlar))
        kayit_id = c.lastrowid
    return {"id": kayit_id, "tarih": tarih, "sinav_turu": sinav_turu,
            "bolum": bolum, "puan": puan, "toplam": toplam}


def deneme_gecmisi(sinav_turu: str = None, limit: int = 10) -> list:
    """Deneme sınavı geçmişini getir."""
    with baglanti() as conn:
        c = conn.cursor()
        if sinav_turu:
            c.execute("""SELECT tarih, sinav_turu, bolum, puan, toplam, notlar
                         FROM deneme_sinav WHERE sinav_turu = ?
                         ORDER BY tarih DESC LIMIT ?""",
                      (sinav_turu.lower(), limit))
        else:
            c.execute("""SELECT tarih, sinav_turu, bolum, puan, toplam, notlar
                         FROM deneme_sinav ORDER BY tarih DESC LIMIT ?""", (limit,))
        rows = c.fetchall()
    return [{"tarih": r["tarih"], "sinav_turu": r["sinav_turu"], "bolum": r["bolum"],
             "puan": r["puan"], "toplam": r["toplam"], "notlar": r["notlar"]} for r in rows]


# ═══════════════════════════════════════════════════════════
# KULLANICI PROFİLİ (ONBOARDING)
# ═══════════════════════════════════════════════════════════

def profil_ayarla(anahtar: str, deger: str):
    """Profil bilgisi kaydet/güncelle."""
    with baglanti() as conn:
        c = conn.cursor()
        c.execute("""INSERT INTO kullanici_profil (anahtar, deger, updated_at)
                     VALUES (?, ?, datetime('now', 'localtime'))
                     ON CONFLICT(anahtar) DO UPDATE SET deger = ?, updated_at = datetime('now', 'localtime')""",
                  (anahtar, deger, deger))


def profil_getir(anahtar: str) -> Optional[str]:
    """Profil bilgisi oku."""
    with baglanti() as conn:
        c = conn.cursor()
        c.execute("SELECT deger FROM kullanici_profil WHERE anahtar = ?", (anahtar,))
        row = c.fetchone()
    return row["deger"] if row else None


def profil_tumu() -> dict:
    """Tüm profil bilgilerini getir."""
    with baglanti() as conn:
        c = conn.cursor()
        c.execute("SELECT anahtar, deger FROM kullanici_profil")
        rows = c.fetchall()
    return {r["anahtar"]: r["deger"] for r in rows}


def onboarding_tamamlandi() -> bool:
    """Kullanıcı tanışma sürecini tamamladı mı?"""
    return profil_getir("onboarding_bitti") == "evet"


# ═══════════════════════════════════════════════════════════
# İSTATİSTİKLER
# ═══════════════════════════════════════════════════════════

def genel_istatistik() -> dict:
    """Genel istatistikleri getir."""
    with baglanti() as conn:
        c = conn.cursor()

        c.execute("SELECT SUM(dakika) as toplam FROM calisma_kayit")
        toplam_calisma = c.fetchone()["toplam"] or 0

        bugun = date.today()
        hafta_basi = bugun - timedelta(days=6)
        c.execute("SELECT SUM(dakika) as toplam FROM calisma_kayit WHERE tarih >= ?",
                  (hafta_basi.isoformat(),))
        hafta_calisma = c.fetchone()["toplam"] or 0

        c.execute("SELECT kilo FROM kilo_kayit ORDER BY tarih ASC LIMIT 1")
        ilk_kilo_row = c.fetchone()
        ilk_kilo = ilk_kilo_row["kilo"] if ilk_kilo_row else None

        c.execute("SELECT kilo FROM kilo_kayit ORDER BY tarih DESC LIMIT 1")
        son_kilo_row = c.fetchone()
        son_kilo_val = son_kilo_row["kilo"] if son_kilo_row else None

        c.execute("SELECT COUNT(*) as sayi FROM gorev_kayit WHERE durum = 'tamamlandi'")
        tamamlanan = c.fetchone()["sayi"]

        c.execute("SELECT COUNT(*) as sayi FROM gorev_kayit")
        toplam_gorev = c.fetchone()["sayi"]

    return {
        "toplam_calisma_dk": toplam_calisma,
        "hafta_calisma_dk": hafta_calisma,
        "ilk_kilo": ilk_kilo,
        "son_kilo": son_kilo_val,
        "tamamlanan_gorev": tamamlanan,
        "toplam_gorev": toplam_gorev,
    }
