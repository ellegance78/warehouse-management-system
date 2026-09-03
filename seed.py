"""
Örnek veri yükleyici — sistemi denemek/sunmak için başlangıç verisi oluşturur.

Bir fabrika deposunun gerçekçi kurulumunu kurar:
  - çalışanlar (admin + depo personeli)
  - 10 depo bölümü ve altlarında raflar
  - 12 fabrika birimi (çıkışların yapıldığı departmanlar)
  - fabrika malzemeleri (hammadde, sarf, yedek parça, kimyasal, ambalaj, KKD)
  - geçmiş tarihli örnek giriş/çıkış hareketleri

Çalıştırma: python seed.py
Uyarı: mevcut veritabanını SIFIRLAR. Eski dosya depo.db.yedek olarak saklanır.
"""

import os
import shutil
from datetime import datetime, timedelta

import config
import db
import auth


def _gun_once(gun, saat=9):
    """N gün önceki bir zaman damgası — hareketleri zamana yaymak için."""
    an = datetime.now() - timedelta(days=gun)
    return an.replace(hour=saat, minute=0, second=0).strftime("%Y-%m-%d %H:%M:%S")


# ------------------------------------------------------------
# DEPO BÖLÜMLERİ
# Fabrika deposu malzemenin CİNSİNE ve saklama koşuluna göre ayrılır.
# (kod, ad, tür, konum, özel koşul, açıklama, raf kodları)
# ------------------------------------------------------------
BOLUMLER = [
    ("HM", "Hammadde Deposu", "hammadde", "A Blok, zemin kat", "",
     "Üretime girecek işlenmemiş malzemeler",
     ["HM-A-01", "HM-A-02", "HM-B-01", "HM-B-02"]),

    ("YM", "Yarı Mamul Deposu", "yari_mamul", "A Blok, zemin kat", "",
     "Ara işlemi bitmiş, montaj bekleyen parçalar",
     ["YM-01", "YM-02"]),

    ("MM", "Mamul (Bitmiş Ürün) Deposu", "mamul", "B Blok, sevkiyat yanı", "",
     "Sevkiyata hazır bitmiş ürünler",
     ["MM-01", "MM-02"]),

    ("SF", "Sarf Malzeme Deposu", "sarf", "B Blok, 1. kat", "",
     "Üretimde tüketilen sarf malzemeler",
     ["SF-A-01", "SF-A-02", "SF-B-01"]),

    ("YP", "Yedek Parça Deposu", "yedek_parca", "Bakım atölyesi yanı", "",
     "Makine yedek parçaları — bakım biriminin kullanımı",
     ["YP-01", "YP-02", "YP-03"]),

    ("KM", "Kimyasal Madde Deposu", "kimyasal", "Dış saha, ayrık bina",
     "Havalandırmalı, yanmaz dolap, MSDS zorunlu",
     "Yanıcı/parlayıcı kimyasallar — İSG kurallarına tabi",
     ["KM-01", "KM-02"]),

    ("AM", "Ambalaj Malzemeleri Deposu", "ambalaj", "C Blok", "",
     "Koli, palet, streç film vb.",
     ["AM-01", "AM-02"]),

    ("KKD", "KKD / İSG Deposu", "kkd", "Giriş kat, İSG ofisi yanı", "",
     "Kişisel koruyucu donanım — zimmetle verilir",
     ["KKD-01", "KKD-02"]),

    ("KRT", "Karantina / Kalite Bekleme Alanı", "karantina", "Mal kabul yanı",
     "Kalite onayı verilmeden üretime gönderilemez",
     "Gelen malın kalite kontrolü beklediği alan",
     ["KRT-01"]),

    ("HRD", "Hurda ve Atık Sahası", "hurda", "Dış saha, arka avlu", "",
     "Fire, hurda ve geri dönüşüm malzemesi",
     ["HRD-01"]),
]

# ------------------------------------------------------------
# FABRİKA BİRİMLERİ — malzemenin hangi birim için çıkarıldığı
# ------------------------------------------------------------
BIRIMLER = [
    ("URT-1", "Üretim Hattı 1", "Vardiya Amiri", "Ana montaj hattı"),
    ("URT-2", "Üretim Hattı 2", "Vardiya Amiri", "İkincil montaj hattı"),
    ("CNC",   "CNC Talaşlı İmalat Atölyesi", "Atölye Şefi", ""),
    ("KYN",   "Kaynakhane", "Kaynak Ustabaşı", ""),
    ("BOY",   "Boyahane", "Boya Sorumlusu", "Toz boya ve fırın hattı"),
    ("BKM",   "Bakım - Onarım", "Bakım Müdürü", "Planlı ve arıza bakımı"),
    ("KKL",   "Kalite Kontrol", "Kalite Şefi", "Numune ve test talepleri"),
    ("ARGE",  "Ar-Ge / Prototip", "Ar-Ge Mühendisi", ""),
    ("SVK",   "Sevkiyat ve Lojistik", "Lojistik Sorumlusu", ""),
    ("IDR",   "İdari İşler / Ofis", "İdari İşler", ""),
    ("TMZ",   "Temizlik ve Genel Hizmetler", "Genel Hizmetler", ""),
    ("ISG",   "İş Sağlığı ve Güvenliği", "İSG Uzmanı", "KKD zimmetleri"),
]

# ------------------------------------------------------------
# MALZEMELER — (stok kodu, ad, kategori, ölçü birimi, kritik stok, açıklama)
# ------------------------------------------------------------
MALZEMELER = [
    ("HM-SAC-001",  "Sac Levha DKP 2mm",          "Hammadde",    "kg",    500, "1000x2000 mm levha"),
    ("HM-ALU-002",  "Alüminyum Profil 40x40",     "Hammadde",    "metre", 200, "6 m boy"),
    ("HM-BOR-003",  "Paslanmaz Boru Ø50",         "Hammadde",    "metre", 100, "304 kalite"),
    ("HM-PLS-004",  "Granül Plastik PP",          "Hammadde",    "kg",    300, "Enjeksiyon için"),

    ("SF-KYN-001",  "Kaynak Teli SG2 1.2mm",      "Sarf",        "kg",     50, "15 kg makara"),
    ("SF-TAS-002",  "Kesme Taşı 230mm",           "Sarf",        "adet",   40, ""),
    ("SF-ELD-003",  "İş Eldiveni (kesilme dirençli)", "Sarf",    "çift",  100, ""),
    ("SF-BEZ-004",  "Endüstriyel Temizlik Bezi",  "Sarf",        "paket",  20, "10'lu paket"),

    ("YP-RLM-001",  "Rulman 6204 2RS",            "Yedek Parça", "adet",   20, ""),
    ("YP-KYS-002",  "V-Kayış A-50",               "Yedek Parça", "adet",   10, ""),
    ("YP-KNT-003",  "Kontaktör 25A",              "Yedek Parça", "adet",    8, "Panolar için"),
    ("YP-HRT-004",  "Hidrolik Hortum 1/2\"",      "Yedek Parça", "metre",  30, ""),

    ("KM-TNR-001",  "Selülozik Tiner",            "Kimyasal",    "litre",  40, "Parlayıcı — F sınıfı"),
    ("KM-YAG-002",  "Endüstriyel Yağ ISO 68",     "Kimyasal",    "litre",  60, "Hidrolik sistemler"),
    ("KM-BOY-003",  "Antipas Astar Boya (Gri)",   "Kimyasal",    "litre",  30, ""),

    ("AM-STR-001",  "Palet Streç Film",           "Ambalaj",     "rulo",   25, "500 mm x 300 m"),
    ("AM-KOL-002",  "Karton Koli 40x30x30",       "Ambalaj",     "adet",  200, ""),
    ("AM-PLT-003",  "Ahşap Palet 80x120",         "Ambalaj",     "adet",   50, "Euro palet"),

    ("HD-CVT-001",  "Cıvata M8x40 (8.8)",         "Hırdavat",    "adet",  500, ""),
    ("HD-SMN-002",  "Somun M8 DIN934",            "Hırdavat",    "adet",  500, ""),
    ("EL-KBL-001",  "NYAF Kablo 2.5mm²",          "Elektrik",    "metre", 200, ""),

    ("KKD-BRT-001", "Baret (Beyaz)",              "KKD",         "adet",   15, "Zimmetle verilir"),
    ("KKD-AYK-002", "Çelik Burunlu İş Ayakkabısı", "KKD",        "çift",   10, ""),
    ("KKD-KLK-003", "Kulak Tıkacı",               "KKD",         "adet",  200, "Tek kullanımlık"),
]


def calistir():
    # Temiz başlangıç: eski db'yi yedekleyip sil
    if os.path.exists(config.VERITABANI_YOLU):
        yedek = config.VERITABANI_YOLU + ".yedek"
        shutil.move(config.VERITABANI_YOLU, yedek)
        print(f"Eski veritabanı yedeklendi: {os.path.basename(yedek)}")
    db.kur()

    with db.baglanti() as conn:
        # --- Çalışanlar ---
        admin = db.calisan_ekle(conn, "admin", auth.sifre_hashle("admin123"),
                                "Sistem Yöneticisi", "admin")
        ahmet = db.calisan_ekle(conn, "ahmet", auth.sifre_hashle("1234"),
                                "Ahmet Yılmaz", "personel")
        elif_ = db.calisan_ekle(conn, "elif", auth.sifre_hashle("1234"),
                                "Elif Kaya", "personel")

        # --- Depo bölümleri ve rafları ---
        raf = {}   # raf kodu -> id
        for kod, ad, tur, konum, kosul, aciklama, raf_kodlari in BOLUMLER:
            bolum_id = db.bolum_ekle(conn, kod, ad, tur, konum, kosul, aciklama)
            for rk in raf_kodlari:
                raf[rk] = db.raf_ekle(conn, bolum_id, rk)

        # --- Fabrika birimleri ---
        birim = {}   # birim kodu -> id
        for kod, ad, sorumlu, aciklama in BIRIMLER:
            birim[kod] = db.birim_ekle(conn, kod, ad, sorumlu, aciklama)

        # --- Malzemeler ---
        urun = {}    # stok kodu -> id
        for kod, ad, kategori, olcu, kritik, aciklama in MALZEMELER:
            urun[kod] = db.urun_ekle(conn, kod, ad, kategori, olcu, kritik, aciklama)

        # --- Mal girişleri: (stok kodu, raf, miktar, çalışan, tedarikçi, irsaliye, kaç gün önce) ---
        girisler = [
            ("HM-SAC-001",  "HM-A-01", 2400, ahmet, "Demir Çelik A.Ş.",  "IRS-2026-0101", 25),
            ("HM-ALU-002",  "HM-A-02",  600, ahmet, "Alüminyum San. Ltd.", "IRS-2026-0104", 24),
            ("HM-BOR-003",  "HM-B-01",  320, elif_, "Paslanmaz Metal",   "IRS-2026-0110", 22),
            ("HM-PLS-004",  "HM-B-02", 1500, elif_, "Polimer Kimya",     "IRS-2026-0112", 20),
            ("SF-KYN-001",  "SF-A-01",  300, ahmet, "Kaynak Market",     "IRS-2026-0118", 18),
            ("SF-TAS-002",  "SF-A-01",  200, ahmet, "Kaynak Market",     "IRS-2026-0118", 18),
            ("SF-ELD-003",  "SF-A-02",  400, elif_, "İSG Ekipman",       "IRS-2026-0121", 17),
            ("SF-BEZ-004",  "SF-B-01",   60, elif_, "Temizlik Tedarik",  "IRS-2026-0122", 17),
            ("YP-RLM-001",  "YP-01",     80, admin, "Rulman Dünyası",    "IRS-2026-0125", 15),
            ("YP-KYS-002",  "YP-01",     40, admin, "Rulman Dünyası",    "IRS-2026-0125", 15),
            ("YP-KNT-003",  "YP-02",     25, admin, "Elektrik Malz.",    "IRS-2026-0130", 14),
            ("YP-HRT-004",  "YP-03",    100, ahmet, "Hidrolik Sistem",   "IRS-2026-0133", 12),
            ("KM-TNR-001",  "KM-01",    200, elif_, "Kimya Tedarik",     "IRS-2026-0140", 11),
            ("KM-YAG-002",  "KM-01",    300, elif_, "Kimya Tedarik",     "IRS-2026-0140", 11),
            ("KM-BOY-003",  "KM-02",    150, elif_, "Boya Sanayi",       "IRS-2026-0142", 10),
            ("AM-STR-001",  "AM-01",    120, ahmet, "Ambalaj Market",    "IRS-2026-0150",  9),
            ("AM-KOL-002",  "AM-01",   1200, ahmet, "Ambalaj Market",    "IRS-2026-0150",  9),
            ("AM-PLT-003",  "AM-02",    300, ahmet, "Palet Sanayi",      "IRS-2026-0151",  8),
            ("HD-CVT-001",  "SF-B-01", 5000, elif_, "Hırdavat Merkezi",  "IRS-2026-0155",  7),
            ("HD-SMN-002",  "SF-B-01", 5000, elif_, "Hırdavat Merkezi",  "IRS-2026-0155",  7),
            ("EL-KBL-001",  "SF-B-01",  800, elif_, "Elektrik Malz.",    "IRS-2026-0157",  6),
            ("KKD-BRT-001", "KKD-01",    60, admin, "İSG Ekipman",       "IRS-2026-0160",  5),
            ("KKD-AYK-002", "KKD-01",    45, admin, "İSG Ekipman",       "IRS-2026-0160",  5),
            ("KKD-KLK-003", "KKD-02",  1000, admin, "İSG Ekipman",       "IRS-2026-0160",  5),
            # Kalite onayı bekleyen parti — karantina bölümünde
            ("HM-SAC-001",  "KRT-01",   800, ahmet, "Yeni Tedarikçi",    "IRS-2026-0162",  3),
        ]
        for kod, rk, miktar, cid, ted, irs, gun in girisler:
            gid = db.giris_ekle(conn, urun[kod], raf[rk], miktar, cid, ted, irs)
            conn.execute("UPDATE giris_kayitlari SET tarih=? WHERE id=?",
                         (_gun_once(gun), gid))

        # --- Mal çıkışları: (stok kodu, raf, miktar, birim, neden, çalışan, teslim alan, gün) ---
        cikislar = [
            ("HM-SAC-001", "HM-A-01", 1200, "URT-1", "Üretimde kullanım", ahmet, "Murat Demir", 19),
            ("HM-SAC-001", "HM-A-01",  600, "CNC",   "Üretimde kullanım", ahmet, "Serkan Ak",   14),
            ("HM-ALU-002", "HM-A-02",  380, "URT-2", "Üretimde kullanım", elif_, "Hakan Öz",    13),
            ("HM-BOR-003", "HM-B-01",  240, "KYN",   "Üretimde kullanım", elif_, "Ali Vural",   12),
            ("HM-PLS-004", "HM-B-02", 1100, "URT-1", "Üretimde kullanım", ahmet, "Murat Demir", 11),
            ("SF-KYN-001", "SF-A-01",  260, "KYN",   "Üretimde kullanım", ahmet, "Ali Vural",   10),
            ("SF-TAS-002", "SF-A-01",  170, "CNC",   "Üretimde kullanım", ahmet, "Serkan Ak",    9),
            ("SF-ELD-003", "SF-A-02",  320, "URT-1", "Zimmet / KKD teslimi", elif_, "Vardiya Amiri", 8),
            ("YP-RLM-001", "YP-01",     65, "BKM",   "Bakım / Onarım",    admin, "Bakım Ekibi",  8),
            ("YP-KYS-002", "YP-01",     33, "BKM",   "Bakım / Onarım",    admin, "Bakım Ekibi",  7),
            ("YP-KNT-003", "YP-02",     20, "BKM",   "Bakım / Onarım",    admin, "Elektrikçi",   6),
            ("KM-TNR-001", "KM-01",     70, "BOY",   "Üretimde kullanım", elif_, "Boya Ustası",  6),
            ("KM-BOY-003", "KM-02",     40, "BOY",   "Üretimde kullanım", elif_, "Boya Ustası",  5),
            ("KM-YAG-002", "KM-01",     60, "BKM",   "Bakım / Onarım",    admin, "Bakım Ekibi",  5),
            ("AM-KOL-002", "AM-01",    900, "SVK",   "Sevkiyat / Satış",  ahmet, "Sevkiyat",     4),
            ("AM-STR-001", "AM-01",    100, "SVK",   "Sevkiyat / Satış",  ahmet, "Sevkiyat",     4),
            ("HM-ALU-002", "HM-A-02",   40, "ARGE",  "Ar-Ge çalışması",   elif_, "Ar-Ge Müh.",   3),
            ("HM-BOR-003", "HM-B-01",   20, "KKL",   "Numune / Test",     elif_, "Kalite Şefi",  3),
            ("KKD-BRT-001","KKD-01",    52, "ISG",   "Zimmet / KKD teslimi", admin, "İSG Uzmanı", 2),
            ("KKD-AYK-002","KKD-01",    38, "ISG",   "Zimmet / KKD teslimi", admin, "İSG Uzmanı", 2),
            ("SF-BEZ-004", "SF-B-01",   45, "TMZ",   "Üretimde kullanım", elif_, "Temizlik",     1),
        ]
        for kod, rk, miktar, bk, neden, cid, teslim, gun in cikislar:
            cid_ = db.cikis_ekle(conn, urun[kod], raf[rk], miktar, birim[bk],
                                 neden, cid, teslim)
            conn.execute("UPDATE cikis_kayitlari SET tarih=? WHERE id=?",
                         (_gun_once(gun, 14), cid_))

    print("Fabrika örnek verisi yüklendi.")
    print(f"  {len(BOLUMLER)} depo bölümü, {len(BIRIMLER)} fabrika birimi, "
          f"{len(MALZEMELER)} malzeme")
    print(f"  {len(girisler)} giriş, {len(cikislar)} çıkış hareketi")
    print("\n  Giriş bilgileri:")
    print("    admin  / admin123  (yönetici)")
    print("    ahmet  / 1234      (depo personeli)")
    print("    elif   / 1234      (depo personeli)")


if __name__ == "__main__":
    calistir()
