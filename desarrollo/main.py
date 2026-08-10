from fastapi import FastAPI, Depends, HTTPException, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from typing import List, Optional
import shutil, os
from datetime import datetime
from collections import defaultdict
import bcrypt

import models
import schemas
from database import engine, get_db

# --- SEGURIDAD CONTRASEÑAS ---
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8')[:72], bcrypt.gensalt()).decode('utf-8')

def verificar_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8')[:72], hashed_password.encode('utf-8'))

app = FastAPI(title="BioMant IA API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("documentos", exist_ok=True)
app.mount("/documentos", StaticFiles(directory="documentos"), name="documentos")

# --- LOGIN ---
@app.post("/login", tags=["Usuarios"])
def iniciar_sesion(datos: schemas.LoginRequest, db: Session = Depends(get_db)):
    usuario = db.query(models.Usuario).filter(models.Usuario.email == datos.email).first()
    if not usuario or not verificar_password(datos.password, usuario.password_hash):
        raise HTTPException(status_code=400, detail="Credenciales incorrectas.")
    if not usuario.activo:
        raise HTTPException(status_code=403, detail="Usuario inactivo.")
    return {
        "mensaje": "Éxito", 
        "usuario": {
            "id": usuario.id, 
            "nombre_completo": usuario.nombre_completo, 
            "rol": usuario.rol, 
            "empresa_id": usuario.empresa_id
        }
    }

# --- EMPRESAS ---
@app.get("/empresas/", tags=["Empresas"])
def listar_empresas(db: Session = Depends(get_db)):
    return db.query(models.Empresa).all()

@app.post("/empresas/", tags=["Empresas"])
def crear_empresa(datos: schemas.EmpresaCreate, db: Session = Depends(get_db)):
    nueva_empresa = models.Empresa(nombre=datos.nombre_empresa, nit=datos.nit, activo=True)
    db.add(nueva_empresa)
    db.commit()
    db.refresh(nueva_empresa)
    return {"mensaje": "Empresa creada con éxito", "id": nueva_empresa.id}

@app.patch("/empresas/{empresa_id}/estado/", tags=["Empresas"])
def cambiar_estado_empresa(empresa_id: int, db: Session = Depends(get_db)):
    empresa = db.query(models.Empresa).filter(models.Empresa.id == empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    empresa.activo = not empresa.activo
    db.commit()
    return {"mensaje": "Estado actualizado", "activo": empresa.activo}

# --- SEDES ---
@app.get("/sedes/", tags=["Sedes"])
def listar_sedes(empresa_id: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(models.Sede)
    if empresa_id:
        query = query.filter(models.Sede.empresa_id == empresa_id)
    return query.all()

@app.post("/sedes/", tags=["Sedes"])
def crear_sede(datos: schemas.SedeCreate, db: Session = Depends(get_db)):
    nueva_sede = models.Sede(
        nombre_sede=datos.nombre_sede,
        empresa_id=datos.empresa_id,
        direccion=datos.direccion or "Sin dirección",
        ciudad=datos.ciudad or "Bogotá"
    )
    db.add(nueva_sede)
    db.commit()
    db.refresh(nueva_sede)
    return {"mensaje": "Sede creada con éxito", "id": nueva_sede.id}

# --- EQUIPOS ---
@app.get("/equipos/", tags=["Inventario"])
def listar_equipos(empresa_id: Optional[int] = None, sede_id: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(models.Equipo)
    if sede_id:
        query = query.filter(models.Equipo.sede_id == sede_id)
    elif empresa_id:
        query = query.join(models.Sede).filter(models.Sede.empresa_id == empresa_id)
    return query.all()

@app.get("/equipos/{equipo_id}", response_model=schemas.EquipoResponse, tags=["Inventario"])
def obtener_equipo(equipo_id: int, db: Session = Depends(get_db)):
    equipo = db.query(models.Equipo).filter(models.Equipo.id == equipo_id).first()
    if not equipo:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")
    return equipo

@app.post("/equipos/{equipo_id}/actualizar/", tags=["Inventario"])
async def actualizar_equipo(
    equipo_id: int, 
    nombre_equipo: str = Form(...),
    marca: Optional[str] = Form(None),
    modelo: Optional[str] = Form(None),
    serie: Optional[str] = Form(None),
    activo_fijo: Optional[str] = Form(None),
    ubicacion_interna: Optional[str] = Form(None),
    invima: Optional[str] = Form(None),
    riesgo: Optional[str] = Form(None),
    proveedor: Optional[str] = Form(None),
    costo: Optional[str] = Form(None),
    adquisicion: Optional[str] = Form(None),         
    tipo_alquiler: Optional[str] = Form(None),       
    periodicidad_mtto: Optional[str] = Form(None),   
    proximo_mtto: Optional[str] = Form(None),
    fecha_inicio_alquiler: Optional[str] = Form(None),
    fecha_fin_alquiler: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    eq = db.query(models.Equipo).filter(models.Equipo.id == equipo_id).first()
    if not eq:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")
    
    eq.nombre_equipo = nombre_equipo
    eq.marca = marca or None
    eq.modelo = modelo or None
    eq.serie = serie or None
    eq.activo_fijo = activo_fijo or None
    eq.ubicacion_interna = ubicacion_interna or None
    eq.registro_sanitario = invima or None
    eq.riesgo = riesgo or None
    eq.proveedor = proveedor or None
    
    try:
        eq.costo_canon = float(costo) if costo and costo != "" else 0.0
    except ValueError:
        eq.costo_canon = 0.0

    eq.adquisicion = adquisicion or "Propio"
    eq.tipo_alquiler = tipo_alquiler or None
    eq.periodicidad_mtto = periodicidad_mtto or "Anual"
    
    try:
        eq.proximo_mtto = datetime.strptime(proximo_mtto, "%Y-%m-%d").date() if proximo_mtto else None
    except ValueError:
        eq.proximo_mtto = None

    try:
        eq.fecha_inicio_alquiler = datetime.strptime(fecha_inicio_alquiler, "%Y-%m-%d").date() if fecha_inicio_alquiler else None
    except ValueError:
        eq.fecha_inicio_alquiler = None

    try:
        eq.fecha_fin_alquiler = datetime.strptime(fecha_fin_alquiler, "%Y-%m-%d").date() if fecha_fin_alquiler else None
    except ValueError:
        eq.fecha_fin_alquiler = None
    
    if eq.fecha_fin_alquiler and eq.fecha_fin_alquiler <= datetime.now().date():
        eq.adquisicion = "Devuelto"

    db.commit()
    return {"mensaje": "Actualizado con éxito"}

@app.post("/equipos/{equipo_id}/foto/", tags=["Inventario"])
async def subir_foto(equipo_id: int, foto: UploadFile = File(...), db: Session = Depends(get_db)):
    ruta = f"documentos/foto_eq_{equipo_id}_{foto.filename}"
    with open(ruta, "wb") as buffer:
        shutil.copyfileobj(foto.file, buffer)
    
    eq = db.query(models.Equipo).filter(models.Equipo.id == equipo_id).first()
    if eq:
        eq.imagen_url = ruta
        db.commit()
    return {"mensaje": "Foto subida", "url": ruta}

# --- GESTIÓN DOCUMENTAL (MANUALES Y PLANOS) ---
@app.post("/equipos/{equipo_id}/documento/", tags=["Documentación"])
async def subir_documento(equipo_id: int, archivo: UploadFile = File(...), db: Session = Depends(get_db)):
    ruta = f"documentos/doc_eq_{equipo_id}_{archivo.filename}"
    with open(ruta, "wb") as buffer: 
        shutil.copyfileobj(archivo.file, buffer)
    
    nuevo_doc = models.DocumentoEquipo(
        equipo_id=equipo_id,
        nombre_archivo=archivo.filename,
        url=ruta
    )
    db.add(nuevo_doc)
    db.commit()
    return {"mensaje": "Documento subido con éxito", "url": ruta}

@app.get("/documentos/equipo/{equipo_id}", tags=["Documentación"])
def listar_documentos(equipo_id: int, db: Session = Depends(get_db)):
    return db.query(models.DocumentoEquipo).filter(models.DocumentoEquipo.equipo_id == equipo_id).all()

@app.delete("/documentos/{doc_id}", tags=["Documentación"])
def eliminar_documento(doc_id: int, db: Session = Depends(get_db)):
    doc = db.query(models.DocumentoEquipo).filter(models.DocumentoEquipo.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    
    if os.path.exists(doc.url):
        os.remove(doc.url)
    
    db.delete(doc)
    db.commit()
    return {"mensaje": "Documento eliminado"}

# --- MANTENIMIENTOS ---
@app.post("/mantenimientos/", tags=["Mantenimiento"])
def crear_mantenimiento(
    equipo_id: int = Form(...), 
    tipo_servicio: str = Form(...), 
    descripcion_trabajo: str = Form(...), 
    costo: float = Form(0.0),
    firma_tecnico: str = Form(...), 
    modalidad: str = Form("Interno"),
    usuario_id: Optional[int] = Form(None), 
    db: Session = Depends(get_db)
):
    mtto = models.Mantenimiento(
        equipo_id=equipo_id, 
        tipo_servicio=tipo_servicio,
        modalidad=modalidad,
        descripcion_trabajo=descripcion_trabajo, 
        costo=costo,
        firma_tecnico=firma_tecnico, 
        usuario_id=usuario_id, 
        fecha_registro=datetime.now().date()
    )
    db.add(mtto)
    db.commit()
    return {"mensaje": "Reporte registrado con éxito"}

@app.get("/mantenimientos/equipo/{equipo_id}", tags=["Mantenimiento"])
def listar_mantenimientos(equipo_id: int, db: Session = Depends(get_db)):
    return db.query(models.Mantenimiento).filter(models.Mantenimiento.equipo_id == equipo_id).all()

# --- TRASLADOS ---
@app.get("/traslados/equipo/{equipo_id}", tags=["Traslados"])
def listar_traslados(equipo_id: int, db: Session = Depends(get_db)):
    return db.query(models.HistorialTraslado).filter(models.HistorialTraslado.equipo_id == equipo_id).all()

# --- DASHBOARD ---
@app.get("/dashboard/metricas/", tags=["Dashboard"])
def obtener_metricas_dashboard(empresa_id: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(models.Equipo)
    if empresa_id:
        query = query.join(models.Sede).filter(models.Sede.empresa_id == empresa_id)
    equipos = query.all()
    
    costo_total_compra = sum(e.costo_canon or 0 for e in equipos if e.adquisicion == "Propio")
    costo_total_alquiler = sum(e.costo_canon or 0 for e in equipos if e.adquisicion == "Alquilado")

    return {
        "total_equipos": len(equipos),
        "costo_total_compra": costo_total_compra,
        "costo_total_alquiler": costo_total_alquiler,
        "desglose_alquiler_proveedor": {},
        "mantenimientos_mes": 0
    }

@app.get("/dashboard/metricas/tecnicos/", tags=["Dashboard"])
def metricas_tecnicos(empresa_id: int, db: Session = Depends(get_db)):
    mantenimientos = db.query(models.Mantenimiento).join(models.Equipo).join(models.Sede).filter(models.Sede.empresa_id == empresa_id).all()
    conteo = defaultdict(int)
    for mtto in mantenimientos:
        if hasattr(mtto, "usuario_id") and mtto.usuario_id:
            conteo[mtto.usuario_id] += 1
    return conteo