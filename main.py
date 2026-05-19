from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator
from typing import Optional, Literal
from datetime import date
import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Kas RW API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", 3306)),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )

class TransaksiBase(BaseModel):
    tanggal: date
    keterangan: str
    jenis: Literal["pemasukan", "pengeluaran"]  # Hanya terima 2 nilai ini
    jumlah: float
    
    @field_validator('jenis')
    @classmethod
    def normalize_jenis(cls, v):
        # Normalisasi: lowercase dan hapus spasi
        v = v.lower().strip()
        if v not in ['pemasukan', 'pengeluaran']:
            raise ValueError('jenis harus "pemasukan" atau "pengeluaran"')
        return v

class TransaksiUpdate(BaseModel):
    tanggal: Optional[date] = None
    keterangan: Optional[str] = None
    jenis: Optional[Literal["pemasukan", "pengeluaran"]] = None
    jumlah: Optional[float] = None
    
    @field_validator('jenis')
    @classmethod
    def normalize_jenis(cls, v):
        if v is not None:
            v = v.lower().strip()
            if v not in ['pemasukan', 'pengeluaran']:
                raise ValueError('jenis harus "pemasukan" atau "pengeluaran"')
        return v

@app.get("/")
def root():
    return {"message": "Kas RW API berjalan"}

@app.get("/transaksi")
def get_all():
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM transaksi ORDER BY tanggal DESC")
    rows = cursor.fetchall()
    db.close()
    return rows

@app.get("/transaksi/{id}")
def get_one(id: int):
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM transaksi WHERE id = %s", (id,))
    row = cursor.fetchone()
    db.close()
    if not row:
        raise HTTPException(status_code=404, detail="Transaksi tidak ditemukan")
    return row

@app.post("/transaksi", status_code=201)
def create(data: TransaksiBase):
    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute(
            "INSERT INTO transaksi (tanggal, keterangan, jenis, jumlah) VALUES (%s, %s, %s, %s)",
            (data.tanggal, data.keterangan, data.jenis, data.jumlah),
        )
        db.commit()
        new_id = cursor.lastrowid
        return {"id": new_id, "message": "Transaksi berhasil ditambahkan"}
    except mysql.connector.Error as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Database error: {str(e)}")
    finally:
        db.close()

@app.put("/transaksi/{id}")
def update(id: int, data: TransaksiUpdate):
    db = get_db()
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM transaksi WHERE id = %s", (id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Transaksi tidak ditemukan")
        
        updated = {**row, **{k: v for k, v in data.dict().items() if v is not None}}
        cursor.execute(
            "UPDATE transaksi SET tanggal=%s, keterangan=%s, jenis=%s, jumlah=%s WHERE id=%s",
            (updated["tanggal"], updated["keterangan"], updated["jenis"], updated["jumlah"], id),
        )
        db.commit()
        return {"message": "Transaksi berhasil diperbarui"}
    except mysql.connector.Error as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Database error: {str(e)}")
    finally:
        db.close()

@app.delete("/transaksi/{id}")
def delete(id: int):
    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute("DELETE FROM transaksi WHERE id = %s", (id,))
        db.commit()
        affected = cursor.rowcount
        if affected == 0:
            raise HTTPException(status_code=404, detail="Transaksi tidak ditemukan")
        return {"message": "Transaksi berhasil dihapus"}
    finally:
        db.close()