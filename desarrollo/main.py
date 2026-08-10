from fastapi import FastAPI, Depends, HTTPException, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import shutil, os
from datetime import datetime
from collections import defaultdict
import bcrypt

# Importaciones de tu estructura
import models
import schemas
from database import engine, get_db

# 1. Crear las tablas automáticamente en la BD al iniciar
models.Base.metadata.create_all(bind=engine)

# 2. Inicializar FastAPI
app = FastAPI(title="BioMant IA API", version="1.0.0")

# --- CONFIGURACIÓN CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- ARCHIVOS ESTÁTICOS Y FRONTEND ---
os.makedirs("documentos", exist_ok=True)
app.mount("/documentos", StaticFiles(directory="documentos"), name="documentos")

# Ruta absoluta hacia la carpeta frontend
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
frontend_path = os.path.join(os.path.dirname(BASE_DIR), "frontend")

# Montar los estáticos del frontend
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")

# Ruta principal para cargar el index.html
@app.get("/")
def leer_index():
    archivo_index = os.path.join(frontend_path, "index.html")
    if os.path.exists(archivo_index):
        return FileResponse(archivo_index)
    return {"error": "index.html no encontrado", "ruta": archivo_index}

# --- SEGURIDAD ---
def verificar_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8')[:72], hashed_password.encode('utf-8'))

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

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
    nueva_empresa = models.Empresa(
        nombre=datos.nombre_empresa, 
        nit=datos.nit, 
        logo_url=datos.logo_url,
        activo=True
    )
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
    return {"mensaje": "Estado de empresa actualizado", "activo": empresa.activo}

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
        ciudad=datos.ciudad or "Bogotá",
        telefono=datos.telefono or "N/A"
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

@app.post("/equipos/", tags=["Inventario"])
def crear_equipo(datos: schemas.EquipoCreate, db: Session = Depends(get_db)):
    nuevo_equipo = models.Equipo(**datos.dict())
    db.add(nuevo_equipo)
    db.commit()
    db.refresh(nuevo_equipo)
    return {"mensaje": "Equipo creado con éxito", "id": nuevo_equipo.id}

@app.get("/equipos/{equipo_id}", tags=["Inventario"])
def obtener_equipo(equipo_id: int, db: Session = Depends(get_db)):
    equipo = db.query(models.Equipo).filter(models.Equipo.id == equipo_id).first()
    if not equipo:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")
    return equipo

# --- GESTIÓN DE USUARIOS ---
@app.get("/usuarios/", tags=["Usuarios"])
def listar_usuarios(empresa_id: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(models.Usuario)
    if empresa_id:
        query = query.filter(models.Usuario.empresa_id == empresa_id)
    return query.all()

@app.post("/usuarios/", tags=["Usuarios"])
def crear_usuario(datos: schemas.UsuarioCreate, db: Session = Depends(get_db)):
    existe = db.query(models.Usuario).filter(models.Usuario.email == datos.email).first()
    if existe:
        raise HTTPException(status_code=400, detail="El correo ya está registrado.")
    
    nuevo_usuario = models.Usuario(
        nombre_completo=datos.nombre_completo,
        email=datos.email,
        password_hash=hash_password(datos.password),
        rol=datos.rol,
        empresa_id=datos.empresa_id,
        activo=True
    )
    db.add(nuevo_usuario)
    db.commit()
    db.refresh(nuevo_usuario)
    return {"mensaje": "Usuario creado con éxito", "id": nuevo_usuario.id}

@app.patch("/usuarios/{usuario_id}/estado", tags=["Usuarios"])
def cambiar_estado_usuario(usuario_id: int, db: Session = Depends(get_db)):
    usuario = db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    usuario.activo = not usuario.activo
    db.commit()
    return {"mensaje": "Estado actualizado", "activo": usuario.activo}

# --- DASHBOARD ---
@app.get("/dashboard/metricas/", tags=["Dashboard"])
def obtener_metricas_dashboard(empresa_id: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(models.Equipo)
    if empresa_id:
        query = query.join(models.Sede).filter(models.Sede.empresa_id == empresa_id)
    equipos = query.all()
    
    return {
        "total_equipos": len(equipos),
        "costo_total_compra": sum(e.costo_canon or 0 for e in equipos if e.adquisicion == "Propio"),
        "costo_total_alquiler": sum(e.costo_canon or 0 for e in equipos if e.adquisicion == "Alquilado"),
        "desglose_alquiler_proveedor": {},
        "mantenimientos_mes": 0
    }

@app.get("/dashboard/metricas/tecnicos/", tags=["Dashboard"])
def metricas_tecnicos(empresa_id: int, db: Session = Depends(get_db)):
    mantenimientos = db.query(models.Mantenimiento).join(models.Equipo).join(models.Sede).filter(models.Sede.empresa_id == empresa_id).all()
    conteo = defaultdict(int)
    for mtto in mantenimientos:
        if mtto.usuario_id: conteo[mtto.usuario_id] += 1
    return conteo
# --- TRASLADOS ---
@app.post("/traslados/", tags=["Traslados"])
def crear_traslado(
    equipo_id: int = Form(...),
    sede_destino_id: int = Form(...),
    ubicacion_destino: str = Form(...),
    motivo: str = Form(...),
    usuario_id: int = Form(...),
    db: Session = Depends(get_db)
):
    equipo = db.query(models.Equipo).filter(models.Equipo.id == equipo_id).first()
    if not equipo:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")
    
    # Registrar el historial del traslado
    nuevo_traslado = models.HistorialTraslado(
        equipo_id=equipo_id,
        sede_origen_id=equipo.sede_id,
        ubicacion_origen=equipo.ubicacion_interna,
        sede_destino_id=sede_destino_id,
        ubicacion_destino=ubicacion_destino,
        motivo=motivo,
        usuario_id=usuario_id
    )
    
    # Actualizar la sede y la ubicación interna actual del equipo
    equipo.sede_id = sede_destino_id
    equipo.ubicacion_interna = ubicacion_destino
    
    db.add(nuevo_traslado)
    db.commit()
    db.refresh(nuevo_traslado)
    
    return {"mensaje": "Traslado registrado con éxito", "id": nuevo_traslado.id}

@app.get("/traslados/equipo/{equipo_id}", tags=["Traslados"])
def listar_traslados_equipo(equipo_id: int, db: Session = Depends(get_db)):
    traslados = db.query(models.HistorialTraslado).filter(models.HistorialTraslado.equipo_id == equipo_id).all()
    return traslados
# --- MANTENIMIENTOS ---
@app.post("/mantenimientos/", tags=["Mantenimientos"])
def crear_mantenimiento(
    equipo_id: int = Form(...),
    tipo_servicio: str = Form(...),
    modalidad: str = Form(...),
    consecutivo_externo: Optional[str] = Form(None),
    proveedor_servicio: Optional[str] = Form(None),
    descripcion_trabajo: str = Form(...),
    costo: float = Form(0.0),
    firma_tecnico: Optional[str] = Form(None),
    usuario_id: Optional[int] = Form(None),
    db: Session = Depends(get_db)
):
    equipo = db.query(models.Equipo).filter(models.Equipo.id == equipo_id).first()
    if not equipo:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")

    nuevo_mtto = models.Mantenimiento(
        equipo_id=equipo_id,
        tipo_servicio=tipo_servicio,
        modalidad=modalidad,
        consecutivo_externo=consecutivo_externo,
        proveedor_servicio=proveedor_servicio,
        descripcion_trabajo=descripcion_trabajo,
        costo=costo,
        firma_tecnico=firma_tecnico,
        usuario_id=usuario_id
    )

    db.add(nuevo_mtto)
    db.commit()
    db.refresh(nuevo_mtto)
    
    return {"mensaje": "Mantenimiento registrado con éxito", "id": nuevo_mtto.id}

@app.get("/mantenimientos/equipo/{equipo_id}", tags=["Mantenimientos"])
def listar_mantenimientos_equipo(equipo_id: int, db: Session = Depends(get_db)):
    mantenimientos = db.query(models.Mantenimiento).filter(models.Mantenimiento.equipo_id == equipo_id).all()
    return mantenimientos