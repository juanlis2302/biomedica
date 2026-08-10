from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# REEMPLAZA 'tu_contraseña' con la contraseña que pusiste al instalar PostgreSQL
SQLALCHEMY_DATABASE_URL = "postgresql://postgres:123456789@localhost:5432/biomant_db"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependencia para obtener la sesión de base de datos en los endpoints
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()