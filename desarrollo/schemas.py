from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field

# --- 1. ESQUEMAS DE EMPRESA ---
class EmpresaBase(BaseModel):
    nombre_empresa: str
    nit: Optional[str] = None
    direccion: Optional[str] = None
    telefono: Optional[str] = None
    logo_url: Optional[str] = None

class EmpresaCreate(EmpresaBase):
    pass

class EmpresaResponse(EmpresaBase):
    id: int
    activo: bool

    class Config:
        from_attributes = True


# --- 2. ESQUEMAS DE SEDE ---
class SedeBase(BaseModel):
    nombre_sede: str
    empresa_id: int
    direccion: Optional[str] = "Sin dirección"
    ciudad: Optional[str] = Field(default="Bogotá")
    telefono: Optional[str] = Field(default="N/A")

class SedeCreate(SedeBase):
    pass

class SedeResponse(SedeBase):
    id: int

    class Config:
        from_attributes = True


# --- 3. ESQUEMAS DE USUARIO ---
class UsuarioBase(BaseModel):
    nombre_completo: str
    email: EmailStr
    rol: str  # 'super_admin', 'admin', 'tecnico'

class UsuarioCreate(UsuarioBase):
    password: str
    empresa_id: Optional[int] = None

class UsuarioResponse(UsuarioBase):
    id: int
    activo: bool
    empresa_id: Optional[int] = None

    class Config:
        from_attributes = True


# --- 4. ESQUEMAS DE EQUIPO ---
class EquipoBase(BaseModel):
    nombre_equipo: str
    marca: str
    modelo: str
    serie: str
    calibracion: bool = False
    activo_fijo: str
    ubicacion_interna: str
    
    registro_sanitario: Optional[str] = None
    riesgo: str  # I, IIa, IIb, III
    adquisicion: str  # Propio / Alquilado
    costo_canon: float = 0.0
    proveedor: Optional[str] = None
    tipo_alquiler: Optional[str] = None
    
    esquema_facturacion: Optional[str] = None
    fecha_inicio_alquiler: Optional[date] = None
    fecha_fin_alquiler: Optional[date] = None
    periodicidad_mtto: str = "Anual"
    imagen_url: Optional[str] = None
    
    ultimo_mtto: Optional[date] = None
    ultima_calibracion: Optional[date] = None
    sede_id: int

class EquipoCreate(EquipoBase):
    pass

class EquipoResponse(EquipoBase):
    id: int

    class Config:
        from_attributes = True


# --- 5. ESQUEMAS DE MANTENIMIENTO ---
class MantenimientoBase(BaseModel):
    tipo_servicio: str  # Preventivo, Correctivo, Calibración
    modalidad: str  # Interno o Externo
    consecutivo_externo: Optional[str] = None
    proveedor_servicio: Optional[str] = None
    descripcion_trabajo: str
    costo: float = 0.0
    firma_tecnico: Optional[str] = None
    pdf_soporte_url: Optional[str] = None

class MantenimientoCreate(MantenimientoBase):
    equipo_id: int
    usuario_id: int

class MantenimientoResponse(MantenimientoBase):
    id: int
    fecha_registro: date
    equipo_id: int
    usuario_id: int

    class Config:
        from_attributes = True


# --- 6. ESQUEMAS DE HISTORIAL DE TRASLADOS ---
class TrasladoBase(BaseModel):
    sede_origen_id: Optional[int] = None
    ubicacion_origen: Optional[str] = None
    sede_destino_id: int
    ubicacion_destino: str
    motivo: Optional[str] = None

class TrasladoCreate(BaseModel):
    equipo_id: int
    sede_destino_id: int
    ubicacion_destino: str
    motivo: str
    usuario_id: Optional[int] = None

class TrasladoResponse(TrasladoBase):
    id: int
    fecha_traslado: datetime
    equipo_id: int
    usuario_id: Optional[int] = None

    class Config:
        from_attributes = True


# --- 7. LOGIN REQUEST ---
class LoginRequest(BaseModel):
    email: str
    password: str

class EmpresaCreate(BaseModel):
    nombre_empresa: str
    nit: Optional[str] = None
    direccion: Optional[str] = None
    telefono: Optional[str] = None