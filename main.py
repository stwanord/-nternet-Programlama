from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from uye import router as uye_router 
from kitap import router as kitap_router
from kitap_yonetimi import router as yonetim_router # Farklı isim verdik

app = FastAPI(
    title="Kütüphane Otomasyonu API",
    description="Kitap ödünç verme, üye yönetimi ve kitap işlemlerini yöneten API sistemi.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routerları benzersiz prefixler ile ekliyoruz
app.include_router(uye_router, prefix="/islemler")
app.include_router(kitap_router, prefix="/kitap") # Kitap işlemleri yolu
app.include_router(yonetim_router, prefix="/kitap-yonetimi") # Admin yönetim yolu

@app.get("/", tags=["Ana Sayfa"])
def ana_sayfa():
    return {"durum": "aktif", "mesaj": "API sorunsuz çalışıyor!"}