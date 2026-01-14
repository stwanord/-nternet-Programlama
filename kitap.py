from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from baglanti import get_db_connection
from yetkilendirme import admin_mi

router = APIRouter()

# --- 1. VERİ MODELLERİ (Önce Tanımlanmalı) ---

class KitapSemasi(BaseModel):
    kitap_adi: str
    yazar_id: int
    kategori_id: int
    isbn: str
    sayfa_sayisi: int

class YazarSemasi(BaseModel):
    yazar_adi: str

class KategoriSemasi(BaseModel):
    kategori_adi: str

# --- 2. EKLEME İŞLEMLERİ (Sadece Admin) ---

@router.post("/ekle", tags=["Kitap İşlemleri"])
def kitap_ekle(
    kitap: KitapSemasi, 
    yapan_rol_id: int = Query(..., description="İşlemi yapanın rol ID'si (Admin=1)")
):
    admin_mi(yapan_rol_id)
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        sorgu = "INSERT INTO Kitaplar (Kitap_adi, Yazar_id, Kategori_id, ISBN, Sayfa_sayisi) VALUES (?, ?, ?, ?, ?)"
        cursor.execute(sorgu, (kitap.kitap_adi, kitap.yazar_id, kitap.kategori_id, kitap.isbn, kitap.sayfa_sayisi))
        conn.commit()
        return {"durum": "basarili", "mesaj": f"'{kitap.kitap_adi}' eklendi!"}
    finally:
        conn.close()

@router.post("/yazar-ekle", tags=["Kitap İşlemleri"])
def yazar_ekle(
    yazar: YazarSemasi, 
    yapan_rol_id: int = Query(..., description="İşlemi yapanın rol ID'si (Admin=1)")
):
    admin_mi(yapan_rol_id)
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO Yazarlar (Yazar_adi) VALUES (?)", (yazar.yazar_adi,))
        conn.commit()
        return {"durum": "basarili", "mesaj": "Yazar eklendi."}
    finally:
        conn.close()

@router.post("/kategori-ekle", tags=["Kitap İşlemleri"])
def kategori_ekle(
    kategori: KategoriSemasi, 
    yapan_rol_id: int = Query(..., description="İşlemi yapanın rol ID'si (Admin=1)")
):
    admin_mi(yapan_rol_id)
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO Kategoriler (Kategori_adi) VALUES (?)", (kategori.kategori_adi,))
        conn.commit()
        return {"durum": "basarili", "mesaj": "Kategori eklendi."}
    finally:
        conn.close()

# --- 3. LİSTELEME VE FİLTRELEME (Herkes Görebilir) ---

@router.get("/listele", tags=["Kitap İşlemleri"])
def kitaplari_listele():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        sorgu = """
        SELECT k.Kitap_id, k.Kitap_adi, y.Yazar_adi, kat.Kategori_adi, k.ISBN, k.Sayfa_sayisi 
        FROM Kitaplar k
        JOIN Yazarlar y ON k.Yazar_id = y.Yazar_id
        JOIN Kategoriler kat ON k.Kategori_id = kat.Kategori_id
        """
        cursor.execute(sorgu)
        rows = cursor.fetchall()
        return [{"id": r[0], "ad": r[1], "yazar": r[2], "kategori": r[3], "isbn": r[4], "sayfa": r[5]} for r in rows]
    finally:
        conn.close()

@router.get("/filtrele", tags=["Kitap İşlemleri"])
def kitap_filtrele(kitap_adi: Optional[str] = None, yazar_adi: Optional[str] = None, kategori_adi: Optional[str] = None):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        sorgu = """
        SELECT k.Kitap_id, k.Kitap_adi, y.Yazar_adi, kat.Kategori_adi, k.ISBN, k.Sayfa_sayisi 
        FROM Kitaplar k
        JOIN Yazarlar y ON k.Yazar_id = y.Yazar_id
        JOIN Kategoriler kat ON k.Kategori_id = kat.Kategori_id
        WHERE 1=1
        """
        params = []
        if kitap_adi: 
            sorgu += " AND k.Kitap_adi LIKE ?"
            params.append(f"%{kitap_adi}%")
        if yazar_adi: 
            sorgu += " AND y.Yazar_adi LIKE ?"
            params.append(f"%{yazar_adi}%")
        if kategori_adi: 
            sorgu += " AND kat.Kategori_adi LIKE ?"
            params.append(f"%{kategori_adi}%")
            
        cursor.execute(sorgu, tuple(params))
        rows = cursor.fetchall()
        return [{"id": r[0], "kitap": r[1], "yazar": r[2], "kategori": r[3], "isbn": r[4]} for r in rows]
    finally:
        conn.close()

# --- 4. GÜNCELLEME VE SİLME (Sadece Admin) ---

@router.put("/guncelle/{kitap_id}", tags=["Kitap İşlemleri"])
def kitap_guncelle(
    kitap_id: int, 
    kitap: KitapSemasi, 
    yapan_rol_id: int = Query(..., description="İşlemi yapanın rol ID'si (Admin=1)")
):
    admin_mi(yapan_rol_id)
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM Kitaplar WHERE Kitap_id = ?", (kitap_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Kitap bulunamadı.")
        
        sorgu = """
        UPDATE Kitaplar SET Kitap_adi = ?, Yazar_id = ?, Kategori_id = ?, ISBN = ?, Sayfa_sayisi = ?
        WHERE Kitap_id = ?
        """
        cursor.execute(sorgu, (kitap.kitap_adi, kitap.yazar_id, kitap.kategori_id, kitap.isbn, kitap.sayfa_sayisi, kitap_id))
        conn.commit()
        return {"durum": "basarili", "mesaj": "Kitap başarıyla güncellendi."}
    finally:
        conn.close()

@router.delete("/sil/{kitap_id}", tags=["Kitap İşlemleri"])
def kitap_sil(
    kitap_id: int, 
    yapan_rol_id: int = Query(..., description="İşlemi yapanın rol ID'si (Admin=1)")
):
    admin_mi(yapan_rol_id)
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM Kitaplar WHERE Kitap_id = ?", (kitap_id,))
        conn.commit()
        return {"durum": "basarili", "mesaj": "Kitap silindi."}
    finally:
        conn.close()