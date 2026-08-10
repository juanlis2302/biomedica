from database import engine, Base
import models

def crear_tablas():
    print("Conectando a la base de datos y creando tablas en orden jerárquico...")
    Base.metadata.create_all(bind=engine)
    print("¡Tablas creadas exitosamente en PostgreSQL!")

if __name__ == "__main__":
    crear_tablas()