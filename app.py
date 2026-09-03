"""
Fabrika Depo Yönetim Yazılımı — Flask uygulaması (tüm route'lar).

Katmanlar:
  - Bu dosya (app.py): HTTP route'ları, form işleme, oturum.
  - db.py: tüm veritabanı sorguları.
  - auth.py: şifre hash + sayfa koruma decorator'ları.
  - config.py: ayarlar ve sabit listeler (bölüm türleri, çıkış nedenleri...).
  - templates/: Jinja2 HTML şablonları.

Uygulamayı ilk kez çalıştırmadan önce örnek veri için: python seed.py
"""

from flask import (Flask, render_template, request, redirect, url_for,
                   session, flash, jsonify, send_file)

import config
import db
import auth
import excel

app = Flask(__name__)
app.secret_key = config.GIZLI_ANAHTAR


@app.context_processor
def sablon_degiskenleri():
    """Bütün şablonlarda kullanılabilecek ortak değerler (bölüm türü etiketleri gibi)."""
    return {"BOLUM_TURLERI": config.BOLUM_TURLERI}


# ============================================================
# KİMLİK DOĞRULAMA (giriş / çıkış)
# ============================================================

@app.route("/giris", methods=["GET", "POST"])
def giris():
    if request.method == "POST":
        kullanici_adi = request.form.get("kullanici_adi", "").strip()
        sifre = request.form.get("sifre", "")
        with db.baglanti() as conn:
            calisan = db.calisan_getir_kullanici_adiyla(conn, kullanici_adi)
        if calisan and auth.sifre_dogru_mu(calisan["sifre_hash"], sifre):
            session["calisan_id"] = calisan["id"]
            session["ad_soyad"] = calisan["ad_soyad"]
            session["rol"] = calisan["rol"]
            flash(f"Hoş geldiniz, {calisan['ad_soyad']}.", "basari")
            return redirect(url_for("ana_sayfa"))
        flash("Kullanıcı adı veya şifre hatalı.", "hata")
    return render_template("login.html")


@app.route("/cikis")
def cikis():
    session.clear()
    flash("Çıkış yapıldı.", "basari")
    return redirect(url_for("giris"))


# ============================================================
# ANA SAYFA (DASHBOARD)
# ============================================================

@app.route("/")
@auth.giris_gerekli
def ana_sayfa():
    with db.baglanti() as conn:
        ozet = db.ozet_sayilar(conn)
        dusuk_stok = db.dusuk_stoklar(conn)
        bolum_ozet = db.bolum_bazli_stok(conn)
        son = db.son_hareketler(conn, limit=10)
    return render_template("index.html", ozet=ozet, dusuk_stok=dusuk_stok,
                           bolum_ozet=bolum_ozet, son_hareketler=son)


# ============================================================
# ÇALIŞANLAR (sadece admin)
# ============================================================

@app.route("/calisanlar", methods=["GET", "POST"])
@auth.admin_gerekli
def calisanlar():
    with db.baglanti() as conn:
        if request.method == "POST":
            ka = request.form.get("kullanici_adi", "").strip()
            ad = request.form.get("ad_soyad", "").strip()
            sifre = request.form.get("sifre", "")
            rol = request.form.get("rol", "personel")
            if not (ka and ad and sifre):
                flash("Tüm alanları doldurun.", "hata")
            elif db.calisan_getir_kullanici_adiyla(conn, ka):
                flash("Bu kullanıcı adı zaten var.", "hata")
            else:
                db.calisan_ekle(conn, ka, auth.sifre_hashle(sifre), ad, rol)
                flash(f"Çalışan eklendi: {ad}", "basari")
            return redirect(url_for("calisanlar"))
        liste = db.calisanlari_listele(conn)
    return render_template("calisanlar.html", calisanlar=liste)


# ============================================================
# FABRİKA BİRİMLERİ (çıkışların yapıldığı departmanlar)
# ============================================================

@app.route("/birimler", methods=["GET", "POST"])
@auth.giris_gerekli
def birimler():
    with db.baglanti() as conn:
        if request.method == "POST":
            kod = request.form.get("kod", "").strip().upper()
            ad = request.form.get("ad", "").strip()
            sorumlu = request.form.get("sorumlu", "").strip()
            aciklama = request.form.get("aciklama", "").strip()
            if not (kod and ad):
                flash("Birim kodu ve adı zorunlu.", "hata")
            else:
                try:
                    db.birim_ekle(conn, kod, ad, sorumlu, aciklama)
                    flash(f"Birim eklendi: {kod} — {ad}", "basari")
                except Exception:
                    flash("Bu birim kodu zaten kullanılıyor.", "hata")
            return redirect(url_for("birimler"))
        liste = db.birimleri_listele(conn)
    return render_template("birimler.html", birimler=liste)


@app.route("/birimler/sil/<int:birim_id>", methods=["POST"])
@auth.admin_gerekli
def birim_sil(birim_id):
    with db.baglanti() as conn:
        try:
            db.birim_sil(conn, birim_id)
            flash("Birim silindi.", "basari")
        except Exception:
            flash("Bu birim silinemedi — çıkış kayıtlarında kullanılıyor.", "hata")
    return redirect(url_for("birimler"))


# ============================================================
# DEPO BÖLÜMLERİ
# ============================================================

@app.route("/bolumler", methods=["GET", "POST"])
@auth.giris_gerekli
def bolumler():
    with db.baglanti() as conn:
        if request.method == "POST":
            kod = request.form.get("kod", "").strip().upper()
            ad = request.form.get("ad", "").strip()
            tur = request.form.get("tur", "genel")
            konum = request.form.get("konum", "").strip()
            ozel_kosul = request.form.get("ozel_kosul", "").strip()
            aciklama = request.form.get("aciklama", "").strip()
            if not (kod and ad):
                flash("Bölüm kodu ve adı zorunlu.", "hata")
            elif tur not in config.BOLUM_TURLERI:
                flash("Geçersiz bölüm türü.", "hata")
            else:
                try:
                    db.bolum_ekle(conn, kod, ad, tur, konum, ozel_kosul, aciklama)
                    flash(f"Bölüm eklendi: {kod} — {ad}", "basari")
                except Exception:
                    flash("Bu bölüm kodu veya adı zaten var.", "hata")
            return redirect(url_for("bolumler"))
        liste = db.bolumleri_listele(conn)
        raflar = db.raflari_listele(conn)
    return render_template("bolumler.html", bolumler=liste, raflar=raflar)


@app.route("/bolumler/sil/<int:bolum_id>", methods=["POST"])
@auth.admin_gerekli
def bolum_sil(bolum_id):
    with db.baglanti() as conn:
        try:
            db.bolum_sil(conn, bolum_id)
            flash("Bölüm silindi.", "basari")
        except Exception:
            flash("Bu bölüm silinemedi — önce içindeki rafları silmelisiniz.", "hata")
    return redirect(url_for("bolumler"))


# ------------------------------------------------------------
# RAFLAR (bölümün alt adresi)
# ------------------------------------------------------------

@app.route("/raflar/ekle", methods=["POST"])
@auth.giris_gerekli
def raf_ekle():
    bolum_id = request.form.get("bolum_id", type=int)
    kod = request.form.get("kod", "").strip().upper()
    aciklama = request.form.get("aciklama", "").strip()
    with db.baglanti() as conn:
        if not (bolum_id and kod):
            flash("Bölüm ve raf kodu zorunlu.", "hata")
        else:
            try:
                db.raf_ekle(conn, bolum_id, kod, aciklama)
                flash(f"Raf eklendi: {kod}", "basari")
            except Exception:
                flash("Bu raf kodu zaten kullanılıyor.", "hata")
    return redirect(url_for("bolumler"))


@app.route("/raflar/sil/<int:raf_id>", methods=["POST"])
@auth.giris_gerekli
def raf_sil(raf_id):
    with db.baglanti() as conn:
        try:
            db.raf_sil(conn, raf_id)
            flash("Raf silindi.", "basari")
        except Exception:
            flash("Bu raf silinemedi — hareket kayıtlarında kullanılıyor.", "hata")
    return redirect(url_for("bolumler"))


# ============================================================
# ÜRÜNLER (fabrika malzemeleri)
# ============================================================

@app.route("/urunler", methods=["GET", "POST"])
@auth.giris_gerekli
def urunler():
    with db.baglanti() as conn:
        if request.method == "POST":
            stok_kodu = request.form.get("stok_kodu", "").strip().upper()
            ad = request.form.get("ad", "").strip()
            kategori = request.form.get("kategori", "").strip()
            birim = request.form.get("birim", "adet").strip()
            kritik = request.form.get("kritik_stok", type=float) or 0
            aciklama = request.form.get("aciklama", "").strip()
            if not (stok_kodu and ad):
                flash("Stok kodu ve malzeme adı zorunlu.", "hata")
            elif kritik < 0:
                flash("Kritik stok negatif olamaz.", "hata")
            else:
                try:
                    db.urun_ekle(conn, stok_kodu, ad, kategori, birim, kritik, aciklama)
                    flash(f"Malzeme eklendi: {stok_kodu} — {ad}", "basari")
                except Exception:
                    flash("Bu stok kodu zaten kullanılıyor.", "hata")
            return redirect(url_for("urunler"))
        liste = db.urunleri_listele(conn)
    return render_template("urunler.html", urunler=liste,
                           birimler=config.OLCU_BIRIMLERI)


# ============================================================
# MAL GİRİŞ — kim koydu / nereye koydu / ne zaman
# ============================================================

@app.route("/mal-giris", methods=["GET", "POST"])
@auth.giris_gerekli
def mal_giris():
    with db.baglanti() as conn:
        if request.method == "POST":
            try:
                urun_id = int(request.form["urun_id"])
                raf_id = int(request.form["raf_id"])
                miktar = float(request.form["miktar"])
            except (KeyError, ValueError):
                flash("Malzeme, raf ve miktar alanlarını doğru doldurun.", "hata")
                return redirect(url_for("mal_giris"))

            tedarikci = request.form.get("tedarikci", "").strip()
            irsaliye_no = request.form.get("irsaliye_no", "").strip()
            aciklama = request.form.get("aciklama", "").strip()

            if miktar <= 0:
                flash("Miktar 0'dan büyük olmalı.", "hata")
            else:
                db.giris_ekle(conn, urun_id, raf_id, miktar,
                              session["calisan_id"], tedarikci, irsaliye_no, aciklama)
                raf = db.raf_getir(conn, raf_id)
                flash(f"Mal girişi kaydedildi → {raf['bolum_ad']} / {raf['kod']}",
                      "basari")
            return redirect(url_for("mal_giris"))

        urunler = db.urunleri_listele(conn)
        bolumler = db.bolumleri_listele(conn)
        raflar = db.raflari_listele(conn)
    return render_template("mal_giris.html", urunler=urunler,
                           bolumler=bolumler, raflar=raflar)


@app.route("/mal-giris/gecmis")
@auth.giris_gerekli
def mal_giris_gecmis():
    f = _giris_filtreleri()
    with db.baglanti() as conn:
        kayitlar = db.giris_gecmisi(conn, f["urun_id"], f["bolum_id"],
                                    baslangic=f["baslangic"],
                                    bitis=_gun_sonu(f["bitis"]))
        urunler = db.urunleri_listele(conn)
        bolumler = db.bolumleri_listele(conn)
    return render_template("mal_giris_gecmis.html", kayitlar=kayitlar,
                           urunler=urunler, bolumler=bolumler,
                           secili_urun=f["urun_id"], secili_bolum=f["bolum_id"],
                           baslangic=f["baslangic"], bitis=f["bitis"])


@app.route("/mal-giris/gecmis/excel")
@auth.giris_gerekli
def mal_giris_excel():
    """Giriş geçmişini Excel olarak indirir — ekrandaki filtrelerin aynısıyla."""
    f = _giris_filtreleri()
    with db.baglanti() as conn:
        kayitlar = db.giris_gecmisi(conn, f["urun_id"], f["bolum_id"],
                                    baslangic=f["baslangic"],
                                    bitis=_gun_sonu(f["bitis"]),
                                    limit=10000)
        not_ = _filtre_notu(conn, f)
    dosya = excel.tabloyu_excele_cevir("Mal Giriş Raporu", excel.GIRIS_SUTUNLARI,
                                       kayitlar, not_)
    return _excel_gonder(dosya, "mal_giris")


# ============================================================
# MAL ÇIKIŞ — kim çıkardı / neden / hangi birim için / nereden / ne zaman
# ============================================================

@app.route("/mal-cikis", methods=["GET", "POST"])
@auth.giris_gerekli
def mal_cikis():
    with db.baglanti() as conn:
        if request.method == "POST":
            try:
                urun_id = int(request.form["urun_id"])
                raf_id = int(request.form["raf_id"])
                miktar = float(request.form["miktar"])
                birim_id = int(request.form["birim_id"])
            except (KeyError, ValueError):
                flash("Malzeme, raf, miktar ve birim alanlarını doğru doldurun.",
                      "hata")
                return redirect(url_for("mal_cikis"))

            neden = request.form.get("neden", "").strip()
            teslim_alan = request.form.get("teslim_alan", "").strip()
            aciklama = request.form.get("aciklama", "").strip()

            mevcut = db.urun_raf_stok(conn, urun_id, raf_id)
            if miktar <= 0:
                flash("Miktar 0'dan büyük olmalı.", "hata")
            elif neden not in config.CIKIS_NEDENLERI:
                flash("Çıkış nedeni seçilmeli.", "hata")
            elif miktar > mevcut:
                # Stok yetersiz — çıkışı ENGELLE (negatif stok oluşmasın)
                raf = db.raf_getir(conn, raf_id)
                flash(f"Yetersiz stok! {raf['kod']} rafında mevcut: {mevcut:g}. "
                      f"Çıkış yapılmadı.", "hata")
            else:
                db.cikis_ekle(conn, urun_id, raf_id, miktar, birim_id, neden,
                              session["calisan_id"], teslim_alan, aciklama)
                flash("Mal çıkışı kaydedildi.", "basari")
            return redirect(url_for("mal_cikis"))

        urunler = db.urunleri_listele(conn)
        bolumler = db.bolumleri_listele(conn)
        raflar = db.raflari_listele(conn)
        birimler = db.birimleri_listele(conn)
    return render_template("mal_cikis.html", urunler=urunler, bolumler=bolumler,
                           raflar=raflar, birimler=birimler,
                           nedenler=config.CIKIS_NEDENLERI)


@app.route("/mal-cikis/gecmis")
@auth.giris_gerekli
def mal_cikis_gecmis():
    f = _cikis_filtreleri()
    with db.baglanti() as conn:
        kayitlar = db.cikis_gecmisi(conn, f["urun_id"], f["bolum_id"], f["birim_id"],
                                    baslangic=f["baslangic"],
                                    bitis=_gun_sonu(f["bitis"]))
        urunler = db.urunleri_listele(conn)
        bolumler = db.bolumleri_listele(conn)
        birimler = db.birimleri_listele(conn)
    return render_template("mal_cikis_gecmis.html", kayitlar=kayitlar,
                           urunler=urunler, bolumler=bolumler, birimler=birimler,
                           secili_urun=f["urun_id"], secili_bolum=f["bolum_id"],
                           secili_birim=f["birim_id"],
                           baslangic=f["baslangic"], bitis=f["bitis"])


@app.route("/mal-cikis/gecmis/excel")
@auth.giris_gerekli
def mal_cikis_excel():
    """Çıkış geçmişini Excel olarak indirir — ekrandaki filtrelerin aynısıyla."""
    f = _cikis_filtreleri()
    with db.baglanti() as conn:
        kayitlar = db.cikis_gecmisi(conn, f["urun_id"], f["bolum_id"], f["birim_id"],
                                    baslangic=f["baslangic"],
                                    bitis=_gun_sonu(f["bitis"]), limit=10000)
        not_ = _filtre_notu(conn, f)
    dosya = excel.tabloyu_excele_cevir("Mal Çıkış Raporu", excel.CIKIS_SUTUNLARI,
                                       kayitlar, not_)
    return _excel_gonder(dosya, "mal_cikis")


# ============================================================
# STOK DURUMU
# ============================================================

@app.route("/stok")
@auth.giris_gerekli
def stok():
    bolum_id = request.args.get("bolum_id", type=int)
    with db.baglanti() as conn:
        detayli = db.stok_durumu(conn, bolum_id)   # ürün + raf kırılımı
        urun_bazli = db.urun_toplam_stok(conn)     # ürün toplamı
        bolumler = db.bolumleri_listele(conn)
    return render_template("stok.html", detayli=detayli, urun_bazli=urun_bazli,
                           bolumler=bolumler, secili_bolum=bolum_id)


# ============================================================
# RAPORLAR
# ============================================================

@app.route("/rapor")
@auth.giris_gerekli
def rapor():
    baslangic = request.args.get("baslangic") or None
    bitis = request.args.get("bitis") or None
    tip = request.args.get("tip") or None
    if tip not in ("giris", "cikis"):
        tip = None
    bitis_sql = _gun_sonu(bitis)
    with db.baglanti() as conn:
        hareketler = db.hareket_raporu(conn, baslangic, bitis_sql, tip)
        birim_tuketim = db.birim_bazli_tuketim(conn, baslangic, bitis_sql)
        neden_dagilim = db.neden_bazli_cikis(conn, baslangic, bitis_sql)
        dusuk = db.dusuk_stoklar(conn)
    return render_template("rapor.html", hareketler=hareketler,
                           birim_tuketim=birim_tuketim,
                           neden_dagilim=neden_dagilim, dusuk=dusuk,
                           baslangic=baslangic, bitis=bitis, tip=tip)


@app.route("/rapor/excel")
@auth.giris_gerekli
def rapor_excel():
    """Birleşik giriş+çıkış hareket raporunu Excel olarak indirir."""
    baslangic = request.args.get("baslangic") or None
    bitis = request.args.get("bitis") or None
    tip = request.args.get("tip") or None
    if tip not in ("giris", "cikis"):
        tip = None
    with db.baglanti() as conn:
        hareketler = db.hareket_raporu(conn, baslangic, _gun_sonu(bitis), tip,
                                       limit=10000)
    parcalar = []
    if baslangic or bitis:
        parcalar.append(f"{baslangic or '...'} — {bitis or '...'}")
    if tip:
        parcalar.append("Sadece giriş" if tip == "giris" else "Sadece çıkış")
    dosya = excel.tabloyu_excele_cevir("Hareket Raporu", excel.HAREKET_SUTUNLARI,
                                       hareketler, " · ".join(parcalar))
    return _excel_gonder(dosya, "hareket_raporu")


@app.route("/stok/excel")
@auth.giris_gerekli
def stok_excel():
    """Raf bazında anlık stok listesini Excel olarak indirir (sayım listesi)."""
    bolum_id = request.args.get("bolum_id", type=int)
    with db.baglanti() as conn:
        satirlar = db.stok_durumu(conn, bolum_id)
        not_ = ""
        if bolum_id:
            bolum = db.bolum_getir(conn, bolum_id)
            if bolum:
                not_ = f"Bölüm: {bolum['kod']} — {bolum['ad']}"
    dosya = excel.tabloyu_excele_cevir("Stok Durumu", excel.STOK_SUTUNLARI,
                                       satirlar, not_)
    return _excel_gonder(dosya, "stok_durumu")


# ============================================================
# YARDIMCI API (formlardaki kademeli seçim için)
# ============================================================

@app.route("/api/raflar/<int:bolum_id>")
@auth.giris_gerekli
def api_raflar(bolum_id):
    """Seçilen bölüme ait rafları JSON döner — formda bölüm seçilince
    raf listesi bununla yenilenir."""
    with db.baglanti() as conn:
        raflar = db.raflari_listele(conn, bolum_id)
    return jsonify([{"id": r["id"], "kod": r["kod"]} for r in raflar])


@app.route("/api/stok/<int:urun_id>/<int:raf_id>")
@auth.giris_gerekli
def api_stok(urun_id, raf_id):
    """Çıkış formunda 'bu rafta ne kadar var' bilgisini anlık göstermek için."""
    with db.baglanti() as conn:
        miktar = db.urun_raf_stok(conn, urun_id, raf_id)
    return jsonify({"stok": miktar})


# ============================================================
# YARDIMCI FONKSİYONLAR
# ============================================================

def _gun_sonu(tarih):
    """Tarih filtresinin bitiş günü de kapsaması için gün sonunu ekler.
    '2026-08-07' → '2026-08-07 23:59:59'"""
    return (tarih + " 23:59:59") if tarih else None


def _giris_filtreleri():
    """Giriş geçmişi filtrelerini URL'den okur.
    Sayfa ve Excel indirme aynı fonksiyonu kullanır — böylece indirilen dosya
    her zaman ekranda görünen listeyle birebir aynı olur."""
    return {
        "urun_id": request.args.get("urun_id", type=int),
        "bolum_id": request.args.get("bolum_id", type=int),
        "birim_id": None,
        "baslangic": request.args.get("baslangic") or None,
        "bitis": request.args.get("bitis") or None,
    }


def _cikis_filtreleri():
    """Çıkış geçmişi filtreleri — girişe ek olarak 'hangi birim' filtresi var."""
    f = _giris_filtreleri()
    f["birim_id"] = request.args.get("birim_id", type=int)
    return f


def _filtre_notu(conn, f):
    """Uygulanan filtreleri Excel'in üst satırına yazmak için okunur metne çevirir.
    Rapor yazdırılınca hangi filtreyle alındığı belli olsun diye."""
    parcalar = []
    if f.get("urun_id"):
        urun = db.urun_getir(conn, f["urun_id"])
        if urun:
            parcalar.append(f"Malzeme: {urun['stok_kodu']} — {urun['ad']}")
    if f.get("bolum_id"):
        bolum = db.bolum_getir(conn, f["bolum_id"])
        if bolum:
            parcalar.append(f"Bölüm: {bolum['kod']} — {bolum['ad']}")
    if f.get("birim_id"):
        birim = conn.execute("SELECT kod, ad FROM birimler WHERE id = ?",
                             (f["birim_id"],)).fetchone()
        if birim:
            parcalar.append(f"Birim: {birim['kod']} — {birim['ad']}")
    if f.get("baslangic") or f.get("bitis"):
        parcalar.append(f"Tarih: {f.get('baslangic') or '...'} — "
                        f"{f.get('bitis') or '...'}")
    return " · ".join(parcalar)


def _excel_gonder(tampon, on_ek):
    """Bellekteki .xlsx dosyasını tarayıcıya indirme olarak gönderir."""
    return send_file(
        tampon,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=excel.dosya_adi(on_ek),
    )


if __name__ == "__main__":
    db.kur()   # tablolar yoksa oluştur
    app.run(host=config.HOST, port=config.PORT, debug=True)
