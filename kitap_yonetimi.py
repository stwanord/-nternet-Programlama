from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from baglanti import get_db_connection
from yetkilendirme import admin_mi

router = APIRouter()

# --- 1. VERİ MODELİ ---
class KitapSemasi(BaseModel):
    ad: str
    yazar_id: int    # Veritabanı şemasına uygun ID girişi
    isbn: str
    kategori_id: int 
    sayfa: int

# --- 2. KİTAP EKLEME (Admin) ---
@router.post("/ekle", tags=["Admin İşlemleri"])
def kitap_ekle(kitap: KitapSemasi, admin_id: int):
    """Sadece Admin yeni kitap ekleyebilir."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Rol kontrolü
        cursor.execute("SELECT Rol_id FROM Kullanicilar WHERE Kullanici_id = ?", (admin_id,))
        kullanici = cursor.fetchone()
        if not kullanici or kullanici[0] != 1:
            raise HTTPException(status_code=403, detail="Bu işlem için yetkiniz yok!")

        sorgu = """
        INSERT INTO Kitaplar (Kitap_adi, Yazar_id, ISBN, Kategori_id, Sayfa_sayisi) 
        VALUES (?, ?, ?, ?, ?)
        """
        cursor.execute(sorgu, (kitap.ad, kitap.yazar_id, kitap.isbn, kitap.kategori_id, kitap.sayfa))
        conn.commit()
        return {"durum": "basarili", "mesaj": "Kitap kütüphaneye eklendi."}
    finally:
        conn.close()

# --- 3. KİTAP SİLME (Admin) ---
@router.delete("/sil/{kitap_id}", tags=["Admin İşlemleri"])
def kitap_sil(kitap_id: int, admin_id: int):
    """Sadece Admin kitap silebilir."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT Rol_id FROM Kullanicilar WHERE Kullanici_id = ?", (admin_id,))
        kullanici = cursor.fetchone()
        if not kullanici or kullanici[0] != 1:
            raise HTTPException(status_code=403, detail="Yetkisiz erişim!")

        cursor.execute("DELETE FROM Kitaplar WHERE Kitap_id = ?", (kitap_id,))
        conn.commit()
        return {"durum": "basarili", "mesaj": "Kitap sistemden silindi."}
    finally:
        conn.close()

# --- 4. KİTAP LİSTELEME (Genel) ---
@router.get("/listele", tags=["Genel"])
def kitaplari_listele():
    """Tüm kitapları yazar ve kategori isimleriyle birlikte getirir."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        sorgu = """
        SELECT k.Kitap_id, k.Kitap_adi, y.Yazar_adi, k.ISBN, kat.Kategori_adi, k.Sayfa_sayisi 
        FROM Kitaplar k
        JOIN Yazarlar y ON k.Yazar_id = y.Yazar_id
        JOIN Kategoriler kat ON k.Kategori_id = kat.Kategori_id
        """
        cursor.execute(sorgu)
        rows = cursor.fetchall()
        return [
            {
                "id": r[0], "ad": r[1], "yazar": r[2], 
                "isbn": r[3], "kategori": r[4], "sayfa": r[5]
            } for r in rows
        ]
    finally:
        conn.close()

# --- 5. ÖDÜNÇ DURUMU TAKİBİ (Yeni Admin Özelliği) ---
@router.get("/odunc-durumu", tags=["Admin İşlemleri"])
def odunc_durumu_listele(admin_id: int):
    """Admin için hangi kitabın kimde olduğunu veya rafta olduğunu gösterir."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Admin yetki kontrolü
        cursor.execute("SELECT Rol_id FROM Kullanicilar WHERE Kullanici_id = ?", (admin_id,))
        kullanici = cursor.fetchone()
        if not kullanici or kullanici[0] != 1:
            raise HTTPException(status_code=403, detail="Bu listeyi görmeye yetkiniz yok!")

        # LEFT JOIN ile tüm kitapları ve aktif ödünç kayıtlarını birleştiriyoruz
        sorgu = """
        SELECT k.Kitap_adi, 
               ISNULL(u.Tam_isim, 'Rafta (Müsait)') as Durum,
               o.Odunc_tarih,
               k.Kitap_id
        FROM Kitaplar k
        LEFT JOIN Odunc_kayitlari o ON k.Kitap_id = o.Kitap_id AND o.Status = 'Ödünçte'
        LEFT JOIN Kullanicilar u ON o.Kullanici_id = u.Kullanici_id
        """
        cursor.execute(sorgu)
        rows = cursor.fetchall()
        return [
            {
                "kitap": r[0], 
                "alan_kisi": r[1], 
                "tarih": str(r[2]) if r[2] else "-", 
                "id": r[3]
            } for r in rows
        ]
    finally:
        conn.close()