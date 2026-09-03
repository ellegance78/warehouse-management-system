"""
Veri katmanı — SQLite bağlantısı, şema kurulumu ve tüm veritabanı sorguları.

Route'lar (app.py) doğrudan SQL yazmaz; buradaki fonksiyonları çağırır. Böylece
veri erişimi tek yerde toplanır, test edilebilir ve staj defterinde "veri katmanı"
diye net gösterilebilir.

Stok tasarımı: stok ayrı tabloda tutulmaz; giriş toplamı - çıkış toplamı olarak
HESAPLANIR. Stok RAF seviyesinde hesaplanır (bkz. urun_raf_stok), bölüm ve ürün
toplamları bu rafların toplanmasıyla elde edilir. Bu, kayıtlarla her zaman
tutarlı ve denetlenebilir bir sonuç verir.
"""

import sqlite3
from contextlib import contextmanager

import config


@contextmanager
def baglanti():
    """Veritabanı bağlantısı açar; iş bitince otomatik commit/kapatma yapar.
    row_factory sayesinde satırlara sütun adıyla erişilir (satir['ad'])."""
    conn = sqlite3.connect(config.VERITABANI_YOLU)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")   # referans bütünlüğü zorlansın
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def kur():
    """schema.sql dosyasını çalıştırarak tabloları (yoksa) oluşturur."""
    import os
    yol = os.path.join(config.PROJE_DIZINI, "schema.sql")
    with open(yol, encoding="utf-8") as f:
        sema = f.read()
    with baglanti() as conn:
        conn.executescript(sema)


# ============================================================
# ÇALIŞANLAR
# ============================================================

def calisan_ekle(conn, kullanici_adi, sifre_hash, ad_soyad, rol="personel"):
    cur = conn.execute(
        "INSERT INTO calisanlar (kullanici_adi, sifre_hash, ad_soyad, rol) "
        "VALUES (?,?,?,?)",
        (kullanici_adi, sifre_hash, ad_soyad, rol),
    )
    return cur.lastrowid


def calisan_getir_kullanici_adiyla(conn, kullanici_adi):
    return conn.execute(
        "SELECT * FROM calisanlar WHERE kullanici_adi = ?", (kullanici_adi,)
    ).fetchone()


def calisan_getir(conn, calisan_id):
    return conn.execute(
        "SELECT * FROM calisanlar WHERE id = ?", (calisan_id,)
    ).fetchone()


def calisanlari_listele(conn):
    return conn.execute("SELECT * FROM calisanlar ORDER BY ad_soyad").fetchall()


# ============================================================
# FABRİKA BİRİMLERİ (çıkışın hangi birim için yapıldığı)
# ============================================================

def birim_ekle(conn, kod, ad, sorumlu="", aciklama=""):
    cur = conn.execute(
        "INSERT INTO birimler (kod, ad, sorumlu, aciklama) VALUES (?,?,?,?)",
        (kod, ad, sorumlu, aciklama),
    )
    return cur.lastrowid


def birimleri_listele(conn):
    return conn.execute("SELECT * FROM birimler ORDER BY kod").fetchall()


def birim_sil(conn, birim_id):
    conn.execute("DELETE FROM birimler WHERE id = ?", (birim_id,))


# ============================================================
# DEPO BÖLÜMLERİ
# ============================================================

def bolum_ekle(conn, kod, ad, tur="genel", konum="", ozel_kosul="", aciklama=""):
    cur = conn.execute(
        "INSERT INTO bolumler (kod, ad, tur, konum, ozel_kosul, aciklama) "
        "VALUES (?,?,?,?,?,?)",
        (kod, ad, tur, konum, ozel_kosul, aciklama),
    )
    return cur.lastrowid


def bolum_guncelle(conn, bolum_id, kod, ad, tur, konum, ozel_kosul, aciklama):
    conn.execute(
        "UPDATE bolumler SET kod=?, ad=?, tur=?, konum=?, ozel_kosul=?, aciklama=? "
        "WHERE id=?",
        (kod, ad, tur, konum, ozel_kosul, aciklama, bolum_id),
    )


def bolum_sil(conn, bolum_id):
    conn.execute("DELETE FROM bolumler WHERE id = ?", (bolum_id,))


def bolum_getir(conn, bolum_id):
    return conn.execute("SELECT * FROM bolumler WHERE id = ?", (bolum_id,)).fetchone()


def bolumleri_listele(conn):
    """Bölümleri, her birinin raf sayısı ve o bölümdeki toplam kalem sayısıyla
    birlikte döner (bölüm listesi sayfası için)."""
    sql = """
        SELECT b.*,
               (SELECT COUNT(*) FROM raflar r WHERE r.bolum_id = b.id) AS raf_sayisi
        FROM bolumler b
        ORDER BY b.kod
    """
    return conn.execute(sql).fetchall()


# ============================================================
# RAFLAR (bölümün alt adresi — stok bu seviyede tutulur)
# ============================================================

def raf_ekle(conn, bolum_id, kod, aciklama=""):
    cur = conn.execute(
        "INSERT INTO raflar (bolum_id, kod, aciklama) VALUES (?,?,?)",
        (bolum_id, kod, aciklama),
    )
    return cur.lastrowid


def raf_sil(conn, raf_id):
    conn.execute("DELETE FROM raflar WHERE id = ?", (raf_id,))


def raflari_listele(conn, bolum_id=None):
    """Rafları bağlı oldukları bölümün adı/kodu ile birlikte döner.
    Formlardaki 'bölüm → raf' kademeli seçimi bu listeden beslenir."""
    sql = """
        SELECT r.id, r.kod, r.aciklama, r.bolum_id,
               b.ad AS bolum_ad, b.kod AS bolum_kod, b.tur AS bolum_tur
        FROM raflar r
        JOIN bolumler b ON b.id = r.bolum_id
    """
    params = []
    if bolum_id:
        sql += " WHERE r.bolum_id = ?"
        params.append(bolum_id)
    sql += " ORDER BY b.kod, r.kod"
    return conn.execute(sql, params).fetchall()


def raf_getir(conn, raf_id):
    return conn.execute(
        "SELECT r.*, b.ad AS bolum_ad, b.kod AS bolum_kod "
        "FROM raflar r JOIN bolumler b ON b.id = r.bolum_id WHERE r.id = ?",
        (raf_id,),
    ).fetchone()


# ============================================================
# ÜRÜNLER (fabrika malzemeleri)
# ============================================================

def urun_ekle(conn, stok_kodu, ad, kategori, birim, kritik_stok=0, aciklama=""):
    cur = conn.execute(
        "INSERT INTO urunler (stok_kodu, ad, kategori, birim, kritik_stok, aciklama) "
        "VALUES (?,?,?,?,?,?)",
        (stok_kodu, ad, kategori, birim, kritik_stok, aciklama),
    )
    return cur.lastrowid


def urunleri_listele(conn):
    return conn.execute("SELECT * FROM urunler ORDER BY stok_kodu").fetchall()


def urun_getir(conn, urun_id):
    return conn.execute("SELECT * FROM urunler WHERE id = ?", (urun_id,)).fetchone()


def urun_sil(conn, urun_id):
    conn.execute("DELETE FROM urunler WHERE id = ?", (urun_id,))


# ============================================================
# MAL GİRİŞ
# ============================================================

def giris_ekle(conn, urun_id, raf_id, miktar, calisan_id,
               tedarikci="", irsaliye_no="", aciklama=""):
    """Bir mal giriş hareketi kaydeder.
    KİM (calisan_id) — NEREYE (raf_id) — NE ZAMAN (tarih, otomatik)."""
    cur = conn.execute(
        "INSERT INTO giris_kayitlari "
        "(urun_id, raf_id, miktar, calisan_id, tedarikci, irsaliye_no, aciklama) "
        "VALUES (?,?,?,?,?,?,?)",
        (urun_id, raf_id, miktar, calisan_id, tedarikci, irsaliye_no, aciklama),
    )
    return cur.lastrowid


def giris_gecmisi(conn, urun_id=None, bolum_id=None, calisan_id=None,
                  baslangic=None, bitis=None, limit=300):
    """Giriş kayıtlarını ürün / raf / bölüm / çalışan adlarıyla birleştirerek döner.
    İsteğe bağlı filtreler uygulanır."""
    sql = """
        SELECT g.id, g.miktar, g.tedarikci, g.irsaliye_no, g.aciklama, g.tarih,
               u.ad AS urun_ad, u.stok_kodu, u.birim,
               r.kod AS raf_kod,
               b.ad AS bolum_ad, b.kod AS bolum_kod,
               c.ad_soyad AS calisan_ad
        FROM giris_kayitlari g
        JOIN urunler u    ON u.id = g.urun_id
        JOIN raflar r     ON r.id = g.raf_id
        JOIN bolumler b   ON b.id = r.bolum_id
        JOIN calisanlar c ON c.id = g.calisan_id
        WHERE 1=1
    """
    params = []
    if urun_id:
        sql += " AND g.urun_id = ?"; params.append(urun_id)
    if bolum_id:
        sql += " AND r.bolum_id = ?"; params.append(bolum_id)
    if calisan_id:
        sql += " AND g.calisan_id = ?"; params.append(calisan_id)
    if baslangic:
        sql += " AND g.tarih >= ?"; params.append(baslangic)
    if bitis:
        sql += " AND g.tarih <= ?"; params.append(bitis)
    sql += " ORDER BY g.tarih DESC, g.id DESC LIMIT ?"; params.append(limit)
    return conn.execute(sql, params).fetchall()


# ============================================================
# MAL ÇIKIŞ
# ============================================================

def cikis_ekle(conn, urun_id, raf_id, miktar, birim_id, neden,
               calisan_id, teslim_alan="", aciklama=""):
    """Bir mal çıkış hareketi kaydeder.
    KİM (calisan_id) — NEDEN (neden) — HANGİ BİRİM İÇİN (birim_id) —
    NEREDEN (raf_id) — NE ZAMAN (tarih, otomatik)."""
    cur = conn.execute(
        "INSERT INTO cikis_kayitlari "
        "(urun_id, raf_id, miktar, birim_id, neden, teslim_alan, calisan_id, aciklama) "
        "VALUES (?,?,?,?,?,?,?,?)",
        (urun_id, raf_id, miktar, birim_id, neden, teslim_alan, calisan_id, aciklama),
    )
    return cur.lastrowid


def cikis_gecmisi(conn, urun_id=None, bolum_id=None, birim_id=None,
                  calisan_id=None, baslangic=None, bitis=None, limit=300):
    sql = """
        SELECT ck.id, ck.miktar, ck.neden, ck.teslim_alan, ck.aciklama, ck.tarih,
               u.ad AS urun_ad, u.stok_kodu, u.birim,
               r.kod AS raf_kod,
               b.ad AS bolum_ad, b.kod AS bolum_kod,
               bi.ad AS birim_ad, bi.kod AS birim_kod,
               c.ad_soyad AS calisan_ad
        FROM cikis_kayitlari ck
        JOIN urunler u    ON u.id = ck.urun_id
        JOIN raflar r     ON r.id = ck.raf_id
        JOIN bolumler b   ON b.id = r.bolum_id
        JOIN birimler bi  ON bi.id = ck.birim_id
        JOIN calisanlar c ON c.id = ck.calisan_id
        WHERE 1=1
    """
    params = []
    if urun_id:
        sql += " AND ck.urun_id = ?"; params.append(urun_id)
    if bolum_id:
        sql += " AND r.bolum_id = ?"; params.append(bolum_id)
    if birim_id:
        sql += " AND ck.birim_id = ?"; params.append(birim_id)
    if calisan_id:
        sql += " AND ck.calisan_id = ?"; params.append(calisan_id)
    if baslangic:
        sql += " AND ck.tarih >= ?"; params.append(baslangic)
    if bitis:
        sql += " AND ck.tarih <= ?"; params.append(bitis)
    sql += " ORDER BY ck.tarih DESC, ck.id DESC LIMIT ?"; params.append(limit)
    return conn.execute(sql, params).fetchall()


# ============================================================
# STOK (hareketlerden HESAPLANIR)
# ============================================================

def urun_raf_stok(conn, urun_id, raf_id):
    """Belirli bir ürünün belirli bir RAFTAKİ anlık stoğu = giriş - çıkış.
    Çıkış yapılmadan önce yeterlilik kontrolü bununla yapılır."""
    giris = conn.execute(
        "SELECT COALESCE(SUM(miktar),0) AS t FROM giris_kayitlari "
        "WHERE urun_id=? AND raf_id=?", (urun_id, raf_id)
    ).fetchone()["t"]
    cikis = conn.execute(
        "SELECT COALESCE(SUM(miktar),0) AS t FROM cikis_kayitlari "
        "WHERE urun_id=? AND raf_id=?", (urun_id, raf_id)
    ).fetchone()["t"]
    return giris - cikis


def stok_durumu(conn, bolum_id=None):
    """Ürün + raf kırılımında anlık stok tablosu (stoğu sıfırdan farklı olanlar).
    'Hangi malzeme, hangi bölümün hangi rafında, ne kadar var' sorusunun cevabı."""
    sql = """
        SELECT u.id AS urun_id, u.ad AS urun_ad, u.stok_kodu, u.birim,
               r.id AS raf_id, r.kod AS raf_kod,
               b.id AS bolum_id, b.ad AS bolum_ad, b.kod AS bolum_kod,
               COALESCE(g.toplam,0) - COALESCE(ck.toplam,0) AS stok
        FROM raflar r
        JOIN bolumler b ON b.id = r.bolum_id
        CROSS JOIN urunler u
        LEFT JOIN (SELECT urun_id, raf_id, SUM(miktar) AS toplam
                   FROM giris_kayitlari GROUP BY urun_id, raf_id) g
               ON g.urun_id = u.id AND g.raf_id = r.id
        LEFT JOIN (SELECT urun_id, raf_id, SUM(miktar) AS toplam
                   FROM cikis_kayitlari GROUP BY urun_id, raf_id) ck
               ON ck.urun_id = u.id AND ck.raf_id = r.id
        WHERE COALESCE(g.toplam,0) - COALESCE(ck.toplam,0) <> 0
    """
    params = []
    if bolum_id:
        sql += " AND b.id = ?"; params.append(bolum_id)
    sql += " ORDER BY b.kod, r.kod, u.ad"
    return conn.execute(sql, params).fetchall()


def bolum_bazli_stok(conn):
    """Bölüm bazında özet: kaç çeşit malzeme var, toplam kaç hareket görmüş."""
    sql = """
        SELECT b.id, b.kod, b.ad, b.tur, b.konum,
               COUNT(DISTINCT s.urun_id) AS cesit
        FROM bolumler b
        LEFT JOIN raflar r ON r.bolum_id = b.id
        LEFT JOIN (
            SELECT urun_id, raf_id, SUM(m) AS bakiye FROM (
                SELECT urun_id, raf_id,  miktar AS m FROM giris_kayitlari
                UNION ALL
                SELECT urun_id, raf_id, -miktar AS m FROM cikis_kayitlari
            ) GROUP BY urun_id, raf_id HAVING SUM(m) > 0
        ) s ON s.raf_id = r.id
        GROUP BY b.id
        ORDER BY b.kod
    """
    return conn.execute(sql).fetchall()


def urun_toplam_stok(conn):
    """Ürün bazında (tüm raflar toplamı) stok — dashboard ve düşük stok için.
    Ürünün kendi kritik_stok değeri 0 ise config'teki varsayılan eşik kullanılır."""
    sql = """
        SELECT u.id AS urun_id, u.ad AS urun_ad, u.stok_kodu, u.birim, u.kategori,
               CASE WHEN u.kritik_stok > 0 THEN u.kritik_stok ELSE ? END AS esik,
               COALESCE(g.toplam,0) - COALESCE(ck.toplam,0) AS stok
        FROM urunler u
        LEFT JOIN (SELECT urun_id, SUM(miktar) AS toplam
                   FROM giris_kayitlari GROUP BY urun_id) g ON g.urun_id = u.id
        LEFT JOIN (SELECT urun_id, SUM(miktar) AS toplam
                   FROM cikis_kayitlari GROUP BY urun_id) ck ON ck.urun_id = u.id
        ORDER BY stok ASC, u.ad
    """
    return conn.execute(sql, (config.VARSAYILAN_KRITIK_STOK,)).fetchall()


def dusuk_stoklar(conn):
    """Stoğu kendi kritik eşiğinin altına düşmüş ürünler."""
    return [u for u in urun_toplam_stok(conn) if u["stok"] < u["esik"]]


# ============================================================
# RAPOR / DASHBOARD
# ============================================================

def hareket_raporu(conn, baslangic=None, bitis=None, tip=None, limit=500):
    """Giriş ve çıkışları tek bir zaman sıralı listede birleştirir.
    Çıkış satırlarında 'hangi birim için' bilgisi de yer alır."""
    sql = """
        SELECT g.tarih, 'GİRİŞ' AS tip,
               u.ad AS urun_ad, u.birim,
               b.ad AS bolum_ad, r.kod AS raf_kod,
               g.miktar,
               c.ad_soyad AS calisan_ad,
               '' AS birim_ad,
               COALESCE(g.tedarikci,'') AS kaynak_hedef,
               COALESCE(g.aciklama,'') AS detay
        FROM giris_kayitlari g
        JOIN urunler u ON u.id = g.urun_id
        JOIN raflar r ON r.id = g.raf_id
        JOIN bolumler b ON b.id = r.bolum_id
        JOIN calisanlar c ON c.id = g.calisan_id
        WHERE (? IS NULL OR g.tarih >= ?) AND (? IS NULL OR g.tarih <= ?)
              AND (? IS NULL OR ? = 'giris')
        UNION ALL
        SELECT ck.tarih, 'ÇIKIŞ' AS tip,
               u.ad, u.birim,
               b.ad, r.kod,
               ck.miktar,
               c.ad_soyad,
               bi.ad,
               COALESCE(ck.neden,''),
               COALESCE(ck.teslim_alan,'')
        FROM cikis_kayitlari ck
        JOIN urunler u ON u.id = ck.urun_id
        JOIN raflar r ON r.id = ck.raf_id
        JOIN bolumler b ON b.id = r.bolum_id
        JOIN birimler bi ON bi.id = ck.birim_id
        JOIN calisanlar c ON c.id = ck.calisan_id
        WHERE (? IS NULL OR ck.tarih >= ?) AND (? IS NULL OR ck.tarih <= ?)
              AND (? IS NULL OR ? = 'cikis')
        ORDER BY tarih DESC
        LIMIT ?
    """
    p = [baslangic, baslangic, bitis, bitis, tip, tip,
         baslangic, baslangic, bitis, bitis, tip, tip, limit]
    return conn.execute(sql, p).fetchall()


def birim_bazli_tuketim(conn, baslangic=None, bitis=None):
    """Hangi fabrika birimi ne kadar malzeme çekmiş — çıkışların birim kırılımı.
    'Hangi birim için çıktı' bilgisinin en görünür karşılığı bu rapordur."""
    sql = """
        SELECT bi.kod, bi.ad,
               COUNT(*) AS hareket_sayisi,
               COUNT(DISTINCT ck.urun_id) AS cesit
        FROM cikis_kayitlari ck
        JOIN birimler bi ON bi.id = ck.birim_id
        WHERE (? IS NULL OR ck.tarih >= ?) AND (? IS NULL OR ck.tarih <= ?)
        GROUP BY bi.id
        ORDER BY hareket_sayisi DESC
    """
    return conn.execute(sql, (baslangic, baslangic, bitis, bitis)).fetchall()


def neden_bazli_cikis(conn, baslangic=None, bitis=None):
    """Çıkışların gerekçe (neden) kırılımı."""
    sql = """
        SELECT ck.neden, COUNT(*) AS hareket_sayisi
        FROM cikis_kayitlari ck
        WHERE (? IS NULL OR ck.tarih >= ?) AND (? IS NULL OR ck.tarih <= ?)
        GROUP BY ck.neden
        ORDER BY hareket_sayisi DESC
    """
    return conn.execute(sql, (baslangic, baslangic, bitis, bitis)).fetchall()


def ozet_sayilar(conn):
    """Dashboard için özet sayılar."""
    def tek(sql):
        return conn.execute(sql).fetchone()["s"]
    return {
        "urun": tek("SELECT COUNT(*) AS s FROM urunler"),
        "bolum": tek("SELECT COUNT(*) AS s FROM bolumler"),
        "raf": tek("SELECT COUNT(*) AS s FROM raflar"),
        "birim": tek("SELECT COUNT(*) AS s FROM birimler"),
        "calisan": tek("SELECT COUNT(*) AS s FROM calisanlar"),
        "bugun_giris": tek("SELECT COUNT(*) AS s FROM giris_kayitlari "
                           "WHERE date(tarih)=date('now')"),
        "bugun_cikis": tek("SELECT COUNT(*) AS s FROM cikis_kayitlari "
                           "WHERE date(tarih)=date('now')"),
    }


def son_hareketler(conn, limit=10):
    """Dashboard'da gösterilen son N hareket."""
    return hareket_raporu(conn, limit=limit)


if __name__ == "__main__":
    kur()
    print(f"Veritabanı kuruldu: {config.VERITABANI_YOLU}")
    with baglanti() as conn:
        tablolar = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        print("Tablolar:", ", ".join(t["name"] for t in tablolar))
