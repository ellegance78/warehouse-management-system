"""
Uygulama ayarları. Tüm sabitler tek yerde toplanır ki modüller sihirli değer
dağıtmasın ve staj defterinde "ayarlar buradan yönetiliyor" diye gösterebilelim.
"""

import os

PROJE_DIZINI = os.path.dirname(os.path.abspath(__file__))

# Veritabanı dosyasının yolu (SQLite — kurulumsuz, tek dosya)
VERITABANI_YOLU = os.path.join(PROJE_DIZINI, "depo.db")

# Flask oturum (session) güvenliği için gizli anahtar.
# Gerçek kullanımda ortam değişkeninden okunur; stajda sabit yeterli.
GIZLI_ANAHTAR = os.environ.get("DEPO_SECRET_KEY", "staj-projesi-gizli-anahtar-degistir")

# Sunucu ayarları
# Not: macOS'ta 5000 portunu AirPlay Receiver (ControlCenter) kullanıyor,
# bu yüzden 5001 seçildi. Ortam değişkeniyle değiştirilebilir.
HOST = "127.0.0.1"
PORT = int(os.environ.get("DEPO_PORT", 5001))

# Ürünün kendi kritik_stok değeri girilmemişse (0) kullanılacak genel eşik
VARSAYILAN_KRITIK_STOK = 10


# ============================================================
# FABRİKA DEPOSU SABİTLERİ
# ============================================================

# Depo bölümü türleri — bölüm eklerken seçilir, listelerde etiket olarak görünür.
# Bir fabrika deposu malzemenin CİNSİNE ve saklama koşuluna göre ayrılır.
BOLUM_TURLERI = {
    "hammadde":    "Hammadde",
    "yari_mamul":  "Yarı Mamul",
    "mamul":       "Mamul (Bitmiş Ürün)",
    "sarf":        "Sarf Malzeme",
    "yedek_parca": "Yedek Parça",
    "kimyasal":    "Kimyasal / Tehlikeli Madde",
    "ambalaj":     "Ambalaj Malzemesi",
    "kkd":         "KKD / İSG Malzemesi",
    "karantina":   "Karantina (Kalite Onayı Bekleyen)",
    "hurda":       "Hurda / Atık",
    "genel":       "Genel",
}

# Mal çıkışının gerekçesi — serbest metin yerine sabit liste, çünkü raporda
# "neden çıktı" kırılımı ancak standart değerlerle anlamlı olur.
CIKIS_NEDENLERI = [
    "Üretimde kullanım",
    "Bakım / Onarım",
    "Numune / Test",
    "Ar-Ge çalışması",
    "Sevkiyat / Satış",
    "Fire / Hurdaya ayırma",
    "Tedarikçiye iade",
    "Zimmet / KKD teslimi",
    "Diğer",
]

# Ürün ölçü birimleri
OLCU_BIRIMLERI = ["adet", "kg", "metre", "litre", "kutu", "paket", "rulo", "çift", "takım"]
