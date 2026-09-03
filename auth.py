"""
Kimlik doğrulama yardımcıları — şifre hash'leme ve sayfa koruma decorator'ları.

Şifreler ASLA düz metin saklanmaz; Werkzeug ile hash'lenir. Oturum (session)
içinde sadece çalışanın id'si, adı ve rolü tutulur.
"""

from functools import wraps

from flask import session, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash


def sifre_hashle(sifre):
    return generate_password_hash(sifre)


def sifre_dogru_mu(sifre_hash, girilen):
    return check_password_hash(sifre_hash, girilen)


def giris_yapildi_mi():
    return "calisan_id" in session


def giris_gerekli(view):
    """Bu decorator ile korunan sayfalar, giriş yapılmadıysa login'e yönlendirir."""
    @wraps(view)
    def sarmalayici(*args, **kwargs):
        if not giris_yapildi_mi():
            flash("Bu sayfa için giriş yapmalısınız.", "uyari")
            return redirect(url_for("giris"))
        return view(*args, **kwargs)
    return sarmalayici


def admin_gerekli(view):
    """Sadece admin rolündeki çalışanların erişebileceği sayfalar için."""
    @wraps(view)
    def sarmalayici(*args, **kwargs):
        if not giris_yapildi_mi():
            flash("Bu sayfa için giriş yapmalısınız.", "uyari")
            return redirect(url_for("giris"))
        if session.get("rol") != "admin":
            flash("Bu işlem için yönetici (admin) yetkisi gerekir.", "hata")
            return redirect(url_for("ana_sayfa"))
        return view(*args, **kwargs)
    return sarmalayici
