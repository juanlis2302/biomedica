from fastapi import FastAPI, Depends, HTTPException, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import shutil, os
from datetime import datetime
from collections import defaultdict
import bcrypt
import pandas as pd
import io

import models
import schemas
from database import engine, get_db

models.Base.metadata.create_all(bind=engine)

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

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
frontend_path = os.path.join(os.path.dirname(BASE_DIR), "frontend")

if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")

@app.get("/")
def leer_index():
    archivo_index = os.path.join(frontend_path, "index.html")
    if os.path.exists(archivo_index):
        return FileResponse(archivo_index)
    return {"error": "index.html no encontrado", "ruta": archivo_index}

def verificar_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8')[:72], hashed_password.encode('utf-8'))

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

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

@app.get("/sedes/", tags=["Sedes"])
def listar_sedes(empresa_id: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(models.Sede)
    if empresa_id:
        query = query.filter(models.Sede.empresa_id == empresa_id)
    return query.all()

@app.post("/sedes/", tags=["Sedes"])
def crear_sede(
    nombre_sede: str = Form(...),
    empresa_id: int = Form(...),
    direccion: str = Form("Sin dirección"),
    ciudad: str = Form("Bogotá"),
    telefono: str = Form("N/A"),
    codigo_prestador: Optional[str] = Form("N/A"),
    db: Session = Depends(get_db)
):
    nueva_sede = models.Sede(
        nombre_sede=nombre_sede,
        empresa_id=empresa_id,
        direccion=direccion,
        ciudad=ciudad,
        telefono=telefono,
        codigo_prestador=codigo_prestador
    )
    db.add(nueva_sede)
    db.commit()
    db.refresh(nueva_sede)
    return {"mensaje": "Sede creada con éxito", "id": nueva_sede.id}

@app.get("/equipos/plantilla/descargar", tags=["Inventario"])
def descargar_plantilla():
    columnas = [
        "nombre_equipo", "marca", "modelo", "serie", "activo_fijo",
        "ubicacion_interna", "registro_sanitario", "riesgo", "adquisicion",
        "costo_canon", "proveedor", "tipo_alquiler", "periodicidad_mtto", "sede_id"
    ]
    df = pd.DataFrame(columns=columnas)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Plantilla_Carga')
    output.seek(0)
    headers = {'Content-Disposition': 'attachment; filename="plantilla_equipos.xlsx"'}
    return StreamingResponse(output, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', headers=headers)

@app.get("/equipos/exportar/", tags=["Inventario"])
def exportar_inventario(empresa_id: Optional[int] = None, sede_id: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(models.Equipo)
    if sede_id:
        query = query.filter(models.Equipo.sede_id == sede_id)
    elif empresa_id:
        query = query.join(models.Sede).filter(models.Sede.empresa_id == empresa_id)
    
    equipos = query.all()
    data = []
    for eq in equipos:
        data.append({
            "ID": eq.id,
            "Sede ID": eq.sede_id,
            "Nombre Equipo": eq.nombre_equipo,
            "Marca": eq.marca,
            "Modelo": eq.modelo,
            "Serie": eq.serie,
            "Activo Fijo": eq.activo_fijo,
            "Ubicación Interna": eq.ubicacion_interna,
            "Registro INVIMA": eq.registro_sanitario,
            "Clasificación Riesgo": eq.riesgo,
            "Adquisición": eq.adquisicion,
            "Proveedor": eq.proveedor,
            "Costo / Canon": eq.costo_canon,
            "Tipo Alquiler": eq.tipo_alquiler,
            "Esquema Facturación": eq.esquema_facturacion,
            "Fecha Inicio Alquiler": eq.fecha_inicio_alquiler.strftime("%Y-%m-%d") if eq.fecha_inicio_alquiler else "N/A",
            "Fecha Fin Alquiler": eq.fecha_fin_alquiler.strftime("%Y-%m-%d") if eq.fecha_fin_alquiler else "N/A",
            "Periodicidad Mtto": eq.periodicidad_mtto,
            "Último Mtto": eq.ultimo_mtto.strftime("%Y-%m-%d") if eq.ultimo_mtto else "N/A",
            "Próximo Mtto": eq.proximo_mtto.strftime("%Y-%m-%d") if eq.proximo_mtto else "N/A",
            "Requiere Calibración": "Sí" if eq.calibracion else "No",
            "Última Calibración": eq.ultima_calibracion.strftime("%Y-%m-%d") if eq.ultima_calibracion else "N/A"
        })
    
    df = pd.DataFrame(data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Inventario_Completo')
    output.seek(0)
    headers = {'Content-Disposition': 'attachment; filename="inventario_completo.xlsx"'}
    return StreamingResponse(output, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', headers=headers)

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
    
    sede = db.query(models.Sede).filter(models.Sede.id == equipo.sede_id).first()
    resultado = equipo.__dict__.copy()
    resultado["nombre_sede"] = sede.nombre_sede if sede else "Sin sede"
    resultado["codigo_prestador"] = sede.codigo_prestador if sede else "N/A"
    return resultado

@app.post("/equipos/{equipo_id}/actualizar/", tags=["Inventario"])
def actualizar_equipo(
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
    costo: float = Form(0.0),
    adquisicion: Optional[str] = Form(None),
    tipo_alquiler: Optional[str] = Form(None),
    periodicidad_mtto: Optional[str] = Form(None),
    proximo_mtto: Optional[str] = Form(None),
    fecha_inicio_alquiler: Optional[str] = Form(None),
    fecha_fin_alquiler: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    equipo = db.query(models.Equipo).filter(models.Equipo.id == equipo_id).first()
    if not equipo:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")
    
    equipo.marca = marca
    equipo.modelo = modelo
    equipo.activo_fijo = activo_fijo
    equipo.ubicacion_interna = ubicacion_interna
    equipo.registro_sanitario = invima
    equipo.riesgo = riesgo
    equipo.proveedor = proveedor
    equipo.costo_canon = costo
    equipo.adquisicion = adquisicion
    equipo.tipo_alquiler = tipo_alquiler
    equipo.periodicidad_mtto = periodicidad_mtto
    
    if proximo_mtto and proximo_mtto.strip():
        equipo.proximo_mtto = datetime.strptime(proximo_mtto, "%Y-%m-%d").date()
    if fecha_inicio_alquiler and fecha_inicio_alquiler.strip():
        equipo.fecha_inicio_alquiler = datetime.strptime(fecha_inicio_alquiler, "%Y-%m-%d").date()
    if fecha_fin_alquiler and fecha_fin_alquiler.strip():
        equipo.fecha_fin_alquiler = datetime.strptime(fecha_fin_alquiler, "%Y-%m-%d").date()

    db.commit()
    return {"mensaje": "Equipo actualizado correctamente"}

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
    return db.query(models.Mantenimiento).filter(models.Mantenimiento.equipo_id == equipo_id).all()

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
    
    nuevo_traslado = models.HistorialTraslado(
        equipo_id=equipo_id,
        sede_origen_id=equipo.sede_id,
        ubicacion_origen=equipo.ubicacion_interna,
        sede_destino_id=sede_destino_id,
        ubicacion_destino=ubicacion_destino,
        motivo=motivo,
        usuario_id=usuario_id
    )
    equipo.sede_id = sede_destino_id
    equipo.ubicacion_interna = ubicacion_destino
    
    db.add(nuevo_traslado)
    db.commit()
    db.refresh(nuevo_traslado)
    return {"mensaje": "Traslado registrado con éxito", "id": nuevo_traslado.id}

@app.get("/traslados/equipo/{equipo_id}", tags=["Traslados"])
def listar_traslados_equipo(equipo_id: int, db: Session = Depends(get_db)):
    return db.query(models.HistorialTraslado).filter(models.HistorialTraslado.equipo_id == equipo_id).all()

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

@app.get("/dashboard/metricas/", tags=["Dashboard"])
def obtener_metricas_dashboard(empresa_id: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(models.Equipo)
    if empresa_id:
        query = query.join(models.Sede).filter(models.Sede.empresa_id == empresa_id)
    equipos = query.all()
    
    costo_compra = sum(e.costo_canon or 0 for e in equipos if e.adquisicion == "Propio")
    costo_alquiler_mensual = sum(e.costo_canon or 0 for e in equipos if e.adquisicion == "Alquilado" and e.tipo_alquiler == "Mensual")
    costo_alquiler_diario = sum(e.costo_canon or 0 for e in equipos if e.adquisicion == "Alquilado" and e.tipo_alquiler == "Por Días")
    
    return {
        "total_equipos": len(equipos),
        "costo_total_compra": costo_compra,
        "costo_alquiler_mensual": costo_alquiler_mensual,
        "costo_alquiler_diario": costo_alquiler_diario,
        "mantenimientos_mes": 0
    }

@app.get("/dashboard/metricas/tecnicos/", tags=["Dashboard"])
def metricas_tecnicos(empresa_id: int, db: Session = Depends(get_db)):
    mantenimientos = db.query(models.Mantenimiento).join(models.Equipo).join(models.Sede).filter(models.Sede.empresa_id == empresa_id).all()
    conteo = defaultdict(int)
    nombres_usuarios = {}
    
    for mtto in mantenimientos:
        if mtto.usuario_id:
            if mtto.usuario_id not in nombres_usuarios:
                usr = db.query(models.Usuario).filter(models.Usuario.id == mtto.usuario_id).first()
                nombres_usuarios[mtto.usuario_id] = usr.nombre_completo if usr else f"Técnico ID: {mtto.usuario_id}"
            
            nombre_tecnico = nombres_usuarios[mtto.usuario_id]
            conteo[nombre_tecnico] += 1
            
    return conteo
# --- DOCUMENTOS Y FOTOS DE EQUIPOS ---
@app.get("/documentos/equipo/{equipo_id}", tags=["Documentos"])
def listar_documentos_equipo(equipo_id: int, db: Session = Depends(get_db)):
    # Si aún no tienes una tabla de documentos en models.py, puedes retornar una lista vacía para que no de error 500 o 404:
    return []

@app.post("/equipos/{equipo_id}/foto/", tags=["Inventario"])
def actualizar_foto_equipo(equipo_id: int, foto: UploadFile = File(...), db: Session = Depends(get_db)):
    equipo = db.query(models.Equipo).filter(models.Equipo.id == equipo_id).first()
    if not equipo:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")
    
    os.makedirs("documentos/fotos", exist_ok=True)
    ruta_archivo = f"documentos/fotos/{equipo_id}_{foto.filename}"
    with open(ruta_archivo, "wb") as buffer:
        shutil.copyfileobj(foto.file, buffer)
        
    equipo.imagen_url = ruta_archivo
    db.commit()
    return {"mensaje": "Foto actualizada", "url": ruta_archivo}

@app.post("/equipos/{equipo_id}/documento/", tags=["Documentos"])
def subir_documento_equipo(equipo_id: int, archivo: UploadFile = File(...), db: Session = Depends(get_db)):
    equipo = db.query(models.Equipo).filter(models.Equipo.id == equipo_id).first()
    if not equipo:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")
        
    os.makedirs("documentos/archivos", exist_ok=True)
    ruta_archivo = f"documentos/archivos/{equipo_id}_{archivo.filename}"
    with open(ruta_archivo, "wb") as buffer:
        shutil.copyfileobj(archivo.file, buffer)
        
    return {"mensaje": "Documento subido con éxito"}
# --- DOCUMENTOS Y FOTOS DE EQUIPOS ---
@app.get("/documentos/equipo/{equipo_id}", tags=["Documentos"])
def listar_documentos_equipo(equipo_id: int, db: Session = Depends(get_db)):
    return []

@app.post("/equipos/{equipo_id}/foto/", tags=["Inventario"])
def actualizar_foto_equipo(equipo_id: int, foto: UploadFile = File(...), db: Session = Depends(get_db)):
    equipo = db.query(models.Equipo).filter(models.Equipo.id == equipo_id).first()
    if not equipo:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")
    
    os.makedirs("documentos/fotos", exist_ok=True)
    ruta_archivo = f"documentos/fotos/{equipo_id}_{foto.filename}"
    with open(ruta_archivo, "wb") as buffer:
        shutil.copyfileobj(foto.file, buffer)
        
    equipo.imagen_url = ruta_archivo
    db.commit()
    return {"mensaje": "Foto actualizada", "url": ruta_archivo}

@app.post("/equipos/{equipo_id}/documento/", tags=["Documentos"])
def subir_documento_equipo(equipo_id: int, archivo: UploadFile = File(...), db: Session = Depends(get_db)):
    equipo = db.query(models.Equipo).filter(models.Equipo.id == equipo_id).first()
    if not equipo:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")
        
    os.makedirs("documentos/archivos", exist_ok=True)
    ruta_archivo = f"documentos/archivos/{equipo_id}_{archivo.filename}"
    with open(ruta_archivo, "wb") as buffer:
        shutil.copyfileobj(archivo.file, buffer)
        
    return {"mensaje": "Documento subido con éxito"}