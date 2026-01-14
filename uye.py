from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from baglanti import get_db_connection
from yetkilendirme import admin_mi

router = APIRouter()

# --- 1. VERİ MODELLERİ ---

class UyeSemasi(BaseModel):
    ad: str
    soyad: str
    eposta: str
    sifre: str
    rol_id: int

class GirisSemasi(BaseModel):
    eposta: str
    sifre: str

# --- 2. KULLANICI İŞLEMLERİ (Kayıt & Giriş) ---

@router.post("/kayit-ol", tags=["Kullanıcı İşlemleri"])
def uye_kayit(uye: UyeSemasi):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        tam_isim = f"{uye.ad} {uye.soyad}"
        sorgu = "INSERT INTO Kullanicilar (Tam_isim, Email, Password, Rol_id) VALUES (?, ?, ?, ?)"
        cursor.execute(sorgu, (tam_isim, uye.eposta, uye.sifre, uye.rol_id))
        conn.commit()
        return {"durum": "basarili", "mesaj": "Kullanıcı başarıyla kaydedildi."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Kayıt hatası: {str(e)}")
    finally:
        conn.close()

@router.post("/giris-yap", tags=["Kullanıcı İşlemleri"])
def uye_giris_yap(giris: GirisSemasi):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        sorgu = "SELECT Kullanici_id, Tam_isim, Rol_id FROM Kullanicilar WHERE Email = ? AND Password = ?"
        cursor.execute(sorgu, (giris.eposta, giris.sifre))
        kullanici = cursor.fetchone()

        if not kullanici:
            raise HTTPException(status_code=401, detail="E-posta veya şifre hatalı!")

        return {
            "durum": "basarili",
            "kullanici": {
                "id": kullanici[0],
                "ad": kullanici[1],
                "rol_id": kullanici[2]
            }
        }
    finally:
        conn.close()

# --- 3. ÖDÜNÇ TALEP VE ONAY İŞLEMLERİ ---

@router.post("/odunc-talep-et", tags=["Kütüphane İşlemleri"])
def kitap_odunc_talep_et(kitap_id: int, kullanici_id: int):
    """Üye kitap için ödünç talebi oluşturur (Status: Beklemede)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Kitap zaten birinde mi veya beklemede bir talebi var mı kontrolü
        cursor.execute("SELECT * FROM Odunc_kayitlari WHERE Kitap_id = ? AND Status IN ('Ödünçte', 'Beklemede')", (kitap_id,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Kitap şu an müsait değil veya bekleyen bir talebi var.")
        
        sorgu = "INSERT INTO Odunc_kayitlari (Kullanici_id, Kitap_id, Odunc_tarih, Status) VALUES (?, ?, GETDATE(), 'Beklemede')"
        cursor.execute(sorgu, (kullanici_id, kitap_id))
        conn.commit()
        return {"durum": "basarili", "mesaj": "Ödünç talebiniz iletildi, admin onayı bekleniyor."}
    finally:
        conn.close()

@router.get("/bekleyen-talepler", tags=["Admin İşlemleri"])
def bekleyen_talepler(admin_id: int):
    """Admin için onay bekleyen tüm talepleri listeler."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Admin yetki kontrolü
        cursor.execute("SELECT Rol_id FROM Kullanicilar WHERE Kullanici_id = ?", (admin_id,))
        admin = cursor.fetchone()
        if not admin or admin[0] != 1:
            raise HTTPException(status_code=403, detail="Bu listeyi görmeye yetkiniz yok!")

        sorgu = """
            SELECT o.Odunc_id, k.Kitap_adi, u.Tam_isim, o.Odunc_tarih 
            FROM Odunc_kayitlari o
            JOIN Kitaplar k ON o.Kitap_id = k.Kitap_id
            JOIN Kullanicilar u ON o.Kullanici_id = u.Kullanici_id
            WHERE o.Status = 'Beklemede'
        """
        cursor.execute(sorgu)
        rows = cursor.fetchall()
        return [{"id": r[0], "kitap": r[1], "uye": r[2], "tarih": str(r[3])} for r in rows]
    finally:
        conn.close()

@router.post("/talep-onayla/{odunc_id}", tags=["Admin İşlemleri"])
def talep_onayla(odunc_id: int):
    """Admin bekleyen talebi onaylar ve kitabı 'Ödünçte' durumuna getirir."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE Odunc_kayitlari SET Status = 'Ödünçte' WHERE Odunc_id = ?", (odunc_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Onaylanacak talep bulunamadı.")
        
        conn.commit()
        return {"durum": "basarili", "mesaj": "Ödünç talebi başarıyla onaylandı."}
    finally:
        conn.close()

@router.post("/talep-reddet/{odunc_id}", tags=["Admin İşlemleri"])
def talep_reddet(odunc_id: int):
    """Admin bekleyen talebi reddeder ve kaydı silerek kitabı boşa çıkarır."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Sadece 'Beklemede' olan talebi siliyoruz
        cursor.execute("DELETE FROM Odunc_kayitlari WHERE Odunc_id = ? AND Status = 'Beklemede'", (odunc_id,))
        
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Reddedilecek uygun talep bulunamadı.")
            
        conn.commit()
        return {"durum": "basarili", "mesaj": "Talep reddedildi ve kitap tekrar erişime açıldı."}
    finally:
        conn.close()

@router.post("/iade-et/{kitap_id}", tags=["Kütüphane İşlemleri"])
def kitap_iade_et(kitap_id: int):
    """Kitabı geri teslim alır ve durumu 'İade Edildi' yapar."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        sorgu = """
            UPDATE Odunc_kayitlari 
            SET Teslim_tarihi = GETDATE(), Status = 'İade Edildi' 
            WHERE Kitap_id = ? AND Status = 'Ödünçte'
        """
        cursor.execute(sorgu, (kitap_id,))
        
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Bu kitap için aktif bir ödünç kaydı bulunamadı.")
        
        conn.commit()
        return {"durum": "basarili", "mesaj": "Kitap başarıyla iade edildi."}
    finally:
        conn.close()

# --- 4. PROFİL SORGULARI ---

@router.get("/aktif-kitaplar/{kullanici_id}", tags=["Üye İşlemleri"])
def aktif_kitaplar(kullanici_id: int):
    """Üyenin şu an elinde olan kitapları listeler."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        sorgu = """
        SELECT k.Kitap_id, k.Kitap_adi, o.Odunc_tarih 
        FROM Odunc_kayitlari o
        JOIN Kitaplar k ON o.Kitap_id = k.Kitap_id
        WHERE o.Kullanici_id = ? AND o.Status = 'Ödünçte'
        """
        cursor.execute(sorgu, (kullanici_id,))
        rows = cursor.fetchall()
        return [{"id": r[0], "ad": r[1], "tarih": str(r[2])} for r in rows]
    finally:
        conn.close()

@router.get("/gecmis-kitaplar/{kullanici_id}", tags=["Üye İşlemleri"])
def gecmis_kitaplar(kullanici_id: int):
    """Üyenin geçmişte iade ettiği kitapları listeler."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        sorgu = """
        SELECT k.Kitap_id, k.Kitap_adi, o.Teslim_tarihi 
        FROM Odunc_kayitlari o
        JOIN Kitaplar k ON o.Kitap_id = k.Kitap_id
        WHERE o.Kullanici_id = ? AND o.Status = 'İade Edildi'
        ORDER BY o.Teslim_tarihi DESC
        """
        cursor.execute(sorgu, (kullanici_id,))
        rows = cursor.fetchall()
        return [{"id": r[0], "ad": r[1], "tarih": str(r[2])} for r in rows]
    finally:
        conn.close()