import datetime
from sqlalchemy import Column, Integer, String, Boolean, Float, Date, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class Empresa(Base):
    __tablename__ = "empresas"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(150), nullable=False)
    nit = Column(String(50), unique=True, nullable=False)
    logo_url = Column(String(255), nullable=True)
    activo = Column(Boolean, default=True)

    # Relaciones
    sedes = relationship("Sede", back_populates="empresa", cascade="all, delete-orphan")
    usuarios = relationship("Usuario", back_populates="empresa", cascade="all, delete-orphan")


class Sede(Base):
    __tablename__ = "sedes"

    id = Column(Integer, primary_key=True, index=True)
    nombre_sede = Column(String(100), nullable=False)
    direccion = Column(String(150), nullable=False)
    ciudad = Column(String(100), nullable=False)
    telefono = Column(String(50), nullable=True)
    codigo_prestador = Column(String(50), nullable=True) # <--- NUEVO CAMPO
    
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False)
    empresa = relationship("Empresa", back_populates="sedes")
    equipos = relationship("Equipo", back_populates="sede")
    
class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    nombre_completo = Column(String(150), nullable=False)
    email = Column(String(150), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    rol = Column(String(50), nullable=False) # 'super_admin', 'admin', 'tecnico'
    activo = Column(Boolean, default=True)

    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=True)

    # Relaciones
    empresa = relationship("Empresa", back_populates="usuarios")
    traslados = relationship("HistorialTraslado", back_populates="usuario")


class Equipo(Base):
    __tablename__ = "equipos"

    id = Column(Integer, primary_key=True, index=True)
    
    # Atributos estandarizados del inventario
    nombre_equipo = Column(String(150), nullable=False)
    marca = Column(String(100), nullable=True)
    modelo = Column(String(100), nullable=True)
    serie = Column(String(100), index=True, nullable=True)
    calibracion = Column(Boolean, default=False) 
    activo_fijo = Column(String(100), nullable=True)
    ubicacion_interna = Column(String(100), nullable=True)
    
    registro_sanitario = Column(String(100), nullable=True) # INVIMA
    riesgo = Column(String(20), nullable=True) # I, IIa, IIb, III
    adquisicion = Column(String(50), default="Propio") # Propio / Alquilado / Devuelto
    costo_canon = Column(Float, default=0.0)
    proveedor = Column(String(150), nullable=True)
    tipo_alquiler = Column(String(50), nullable=True) # Mensual / Por Días
    
    # Fechas y control de alquileres
    esquema_facturacion = Column(String(50), nullable=True)
    fecha_inicio_alquiler = Column(Date, nullable=True)
    fecha_fin_alquiler = Column(Date, nullable=True) # <--- CORREGIDO: Añadido para la devolución desde Hoja de Vida
    periodicidad_mtto = Column(String(50), default="Anual") 
    imagen_url = Column(String(255), nullable=True) 
    
    # Fechas automáticas de control
    ultimo_mtto = Column(Date, nullable=True)
    proximo_mtto = Column(Date, nullable=True) 
    ultima_calibracion = Column(Date, nullable=True)

    # Llaves foráneas
    sede_id = Column(Integer, ForeignKey("sedes.id"), nullable=False)

    # Relaciones
    sede = relationship("Sede", back_populates="equipos")
    mantenimientos = relationship("Mantenimiento", back_populates="equipo", cascade="all, delete-orphan")
    traslados = relationship("HistorialTraslado", back_populates="equipo", cascade="all, delete-orphan")


class Mantenimiento(Base):
    __tablename__ = "mantenimientos"

    id = Column(Integer, primary_key=True, index=True)
    tipo_servicio = Column(String(50), nullable=False) 
    modalidad = Column(String(50), nullable=False) 
    consecutivo_externo = Column(String(100), nullable=True) 
    proveedor_servicio = Column(String(150), nullable=True)
    descripcion_trabajo = Column(String(500), nullable=False)
    costo = Column(Float, default=0.0)
    pdf_soporte_url = Column(String(255), nullable=True) 
    firma_tecnico = Column(Text, nullable=True) 
    fecha_registro = Column(Date, default=datetime.date.today)

    # Llave foránea para el conteo de reportes por técnico
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True) # <--- ASEGURADO para métricas de técnicos

    equipo_id = Column(Integer, ForeignKey("equipos.id"), nullable=False)
    equipo = relationship("Equipo", back_populates="mantenimientos")


class HistorialTraslado(Base):
    __tablename__ = "historial_traslados"

    id = Column(Integer, primary_key=True, index=True)
    sede_origen_id = Column(Integer, ForeignKey("sedes.id"), nullable=True)
    ubicacion_origen = Column(String(100), nullable=True)
    sede_destino_id = Column(Integer, ForeignKey("sedes.id"), nullable=False)
    ubicacion_destino = Column(String(100), nullable=False)
    fecha_traslado = Column(DateTime, default=datetime.datetime.utcnow)
    motivo = Column(String(255), nullable=True)

    equipo_id = Column(Integer, ForeignKey("equipos.id"), nullable=False)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)

    equipo = relationship("Equipo", back_populates="traslados")
    usuario = relationship("Usuario", back_populates="traslados")
    sede_origen = relationship("Sede", foreign_keys=[sede_origen_id])
    sede_destino = relationship("Sede", foreign_keys=[sede_destino_id])