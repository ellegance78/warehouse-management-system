🇹🇷 **Türkçe** · [🇬🇧 English](README.md)

# Depo Yönetim Yazılımı

Bir fabrika deposunda kâğıt defterin yerini alan, her malzeme hareketini uçtan
uca izlenebilir kılan tam yığın web uygulaması.

Entegre bir demir-çelik tesisinde, yaz stajı kapsamında geliştirildi.

---

## İki soru

Bütün tasarım bu ikisini eksiksiz cevaplamak için var:

- **Girişte** — hangi malzeme, kim tarafından, nereye, ne zaman?
- **Çıkışta** — hangi malzeme, kim tarafından, **neden**, **hangi birim için**,
  nereden, ne zaman?

![Veritabanı şeması](docs/database-schema.png)

Giriş ve çıkış ayrı tablolarda; çünkü çıkış kaydı girişte bulunmayan iki alan
taşıyor: çıkış nedeni ve talep eden birim.

## Savunulmaya değer tasarım kararları

**Stok hiçbir yerde tutulmuyor.** Her okumada hareket kayıtlarından hesaplanıyor.
Böylece stok rakamı ile hareket geçmişi arasında tutarsızlık oluşması yapısal
olarak imkânsız — ayrı bir stok kolonu, atlanan ilk güncellemede sessizce
kayardı.

**Stok denetimi raf bazında, ürün bazında değil.** Depoda o malzemeden 300 adet
olabilir; ama o rafta 20 varsa oradan 50 çıkaramazsın. Aşırı çıkış engellenir ve
rafta gerçekte ne kaldığı söylenir.

**Çıkış nedeni dokuz seçeneklik sabit listeden.** Serbest metin olsaydı raporda
"üretim", "üretimde" ve "ÜRETİM" üç ayrı satır olur, kırılım anlamsızlaşırdı.

**Formlarda kademeli seçim.** Önce bölüm seçilir, o bölümün rafları JavaScript
ile yüklenir, sonra malzeme ve miktar girilir — yanlış bölümün rafına kayıt
yapılamaz.

**Yetki denetimi sunucu tarafında.** Menü öğesini gizlemek sunumdur, güvenlik
değil; yönetici rotaları bir dekoratörle korunuyor.

## Ekranlar

| Ana sayfa | Mal giriş |
|---|---|
| ![](docs/dashboard.png) | ![](docs/goods-receipt.png) |

Ana sayfa kritik stok uyarılarını, bölüm doluluklarını ve son hareketleri
gösteriyor. Raporlama ekranı çıkışları birim ve neden kırılımında veriyor;
tarih filtresi ve **dört ekranın da Excel çıktısı** var — depo sorumlusu
verileri kendi çalışma dosyalarında kullanmak istiyordu.

## Teknoloji

Python · Flask · SQLite · Jinja2 · saf JavaScript — derleme adımı yok, ayrı
veritabanı sunucusu yok. Parolalar özet (hash) olarak saklanıyor; her kayıt onu
yapan çalışanı taşıyor.

**7 tablo · 22 rota · 12 ekran · 4 Excel çıktısı**

## Çalıştırma

```bash
python -m venv venv && venv/bin/pip install -r requirements.txt
venv/bin/python seed.py     # örnek fabrika verisi
venv/bin/python app.py      # → http://localhost:5001
```

Demo kullanıcıları `seed.py` oluşturur. macOS'ta 5000 portunu AirPlay Receiver
kullandığı için uygulama 5001'de çalışır; `DEPO_PORT` ile değiştirilebilir.

Arayüz ve kod yorumları Türkçe, belgelendirme iki dilde.
