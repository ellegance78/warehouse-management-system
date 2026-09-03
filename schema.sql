-- ============================================================
-- Fabrika Depo Yönetim Yazılımı — Veritabanı Şeması (SQLite)
-- ============================================================
-- Tasarım ilkeleri:
--
-- 1) Stok DOĞRUDAN tutulmaz; giriş ve çıkış hareketlerinden HESAPLANIR
--    (defter/ledger mantığı). Böylece stok her zaman kayıtlarla tutarlıdır
--    ve "bu stok nereden geldi" sorusu her zaman izlenebilir.
--
-- 2) Depo adresi İKİ seviyelidir: bölüm (Hammadde Deposu) → raf (HM-A-01).
--    Stok raf seviyesinde tutulur, bölüm toplamı raflardan toplanır. Fabrika
--    deposunda "nereye koydun" sorusunun cevabı bir raf adresidir.
--
-- 3) Çıkış her zaman bir FABRİKA BİRİMİ için yapılır (Üretim Hattı 1, Bakım,
--    Kalite vb.). Birim serbest metin değil ayrı tablodur; böylece "bu ay
--    Bakım birimi ne kadar yedek parça çekti" sorulabilir.

-- ------------------------------------------------------------
-- Çalışanlar (kullanıcılar) — sisteme giriş yapan ve kayıt tutan kişiler
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS calisanlar (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    kullanici_adi   TEXT NOT NULL UNIQUE,
    sifre_hash      TEXT NOT NULL,               -- şifre asla düz metin tutulmaz
    ad_soyad        TEXT NOT NULL,
    rol             TEXT NOT NULL DEFAULT 'personel',  -- 'admin' | 'personel'
    olusturma       TEXT DEFAULT CURRENT_TIMESTAMP
);

-- ------------------------------------------------------------
-- Fabrika birimleri — malzemenin HANGİ BİRİM İÇİN çıkarıldığı
-- (masraf yeri / talep eden departman)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS birimler (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    kod         TEXT NOT NULL UNIQUE,            -- örn. "URT-1", "BKM"
    ad          TEXT NOT NULL,                   -- örn. "Üretim Hattı 1"
    sorumlu     TEXT,                            -- birim sorumlusu (bilgi amaçlı)
    aciklama    TEXT,
    olusturma   TEXT DEFAULT CURRENT_TIMESTAMP
);

-- ------------------------------------------------------------
-- Depo bölümleri — deponun ana ayrımı (malzeme türüne göre)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS bolumler (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    kod         TEXT NOT NULL UNIQUE,            -- örn. "HM", "YP", "KM"
    ad          TEXT NOT NULL UNIQUE,            -- örn. "Hammadde Deposu"
    tur         TEXT NOT NULL DEFAULT 'genel',   -- hammadde|yari_mamul|mamul|sarf|
                                                 -- yedek_parca|kimyasal|ambalaj|
                                                 -- kkd|karantina|hurda|genel
    konum       TEXT,                            -- fabrika içindeki fiziksel yer
    ozel_kosul  TEXT,                            -- örn. "Yanmaz dolap, havalandırmalı"
    aciklama    TEXT,
    olusturma   TEXT DEFAULT CURRENT_TIMESTAMP
);

-- ------------------------------------------------------------
-- Raflar / gözler — bölümün alt adresi. Stok BU seviyede tutulur.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS raflar (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    bolum_id    INTEGER NOT NULL REFERENCES bolumler(id),
    kod         TEXT NOT NULL UNIQUE,            -- örn. "HM-A-01"
    aciklama    TEXT,
    olusturma   TEXT DEFAULT CURRENT_TIMESTAMP
);

-- ------------------------------------------------------------
-- Ürünler (fabrika malzemeleri)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS urunler (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    stok_kodu     TEXT NOT NULL UNIQUE,          -- örn. "HM-SAC-002"
    ad            TEXT NOT NULL,
    kategori      TEXT,                          -- örn. "Hammadde", "Yedek Parça"
    birim         TEXT NOT NULL DEFAULT 'adet',  -- 'adet' | 'kg' | 'metre' | 'litre'...
    kritik_stok   REAL NOT NULL DEFAULT 0,       -- bunun altına düşerse uyarı
    aciklama      TEXT,
    olusturma     TEXT DEFAULT CURRENT_TIMESTAMP
);

-- ------------------------------------------------------------
-- MAL GİRİŞ — depoya malzeme girişi
-- Kim koydu (calisan_id), nereye koydu (raf_id → bolum), ne zaman (tarih)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS giris_kayitlari (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    urun_id      INTEGER NOT NULL REFERENCES urunler(id),
    raf_id       INTEGER NOT NULL REFERENCES raflar(id),      -- NEREYE koyuldu
    miktar       REAL NOT NULL CHECK (miktar > 0),
    calisan_id   INTEGER NOT NULL REFERENCES calisanlar(id),  -- KİM koydu
    tedarikci    TEXT,                                        -- kimden geldi
    irsaliye_no  TEXT,                                        -- belge takibi
    aciklama     TEXT,
    tarih        TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP      -- NE ZAMAN
);

-- ------------------------------------------------------------
-- MAL ÇIKIŞ — depodan malzeme çıkışı
-- Kim çıkardı (calisan_id), neden (neden), hangi birim için (birim_id),
-- ne zaman (tarih), nereden (raf_id → bolum)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS cikis_kayitlari (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    urun_id      INTEGER NOT NULL REFERENCES urunler(id),
    raf_id       INTEGER NOT NULL REFERENCES raflar(id),      -- NEREDEN çıktı
    miktar       REAL NOT NULL CHECK (miktar > 0),
    birim_id     INTEGER NOT NULL REFERENCES birimler(id),    -- HANGİ BİRİM için
    neden        TEXT NOT NULL,                               -- NEDEN çıkarıldı
    teslim_alan  TEXT,                                        -- malzemeyi teslim alan kişi
    calisan_id   INTEGER NOT NULL REFERENCES calisanlar(id),  -- KİM çıkardı
    aciklama     TEXT,
    tarih        TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP      -- NE ZAMAN
);

-- ------------------------------------------------------------
-- Sık sorgulanan sütunlar için indeksler (performans)
-- ------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_raf_bolum     ON raflar(bolum_id);
CREATE INDEX IF NOT EXISTS idx_giris_urun    ON giris_kayitlari(urun_id);
CREATE INDEX IF NOT EXISTS idx_giris_raf     ON giris_kayitlari(raf_id);
CREATE INDEX IF NOT EXISTS idx_giris_tarih   ON giris_kayitlari(tarih);
CREATE INDEX IF NOT EXISTS idx_cikis_urun    ON cikis_kayitlari(urun_id);
CREATE INDEX IF NOT EXISTS idx_cikis_raf     ON cikis_kayitlari(raf_id);
CREATE INDEX IF NOT EXISTS idx_cikis_birim   ON cikis_kayitlari(birim_id);
CREATE INDEX IF NOT EXISTS idx_cikis_tarih   ON cikis_kayitlari(tarih);
