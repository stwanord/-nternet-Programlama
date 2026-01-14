from fastapi import HTTPException

def admin_mi(rol_id: int):
    """
    Kullanıcının admin (kütüphaneci) olup olmadığını kontrol eder.
    rol_id = 1 ise Admin, değilse yetkisizdir.
    """
    if rol_id != 1:
        raise HTTPException(
            status_code=403, 
            detail="Bu işlem için yetkiniz yok. Sadece kütüphaneciler yapabilir."
        )
    return True