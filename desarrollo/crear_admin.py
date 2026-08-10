import bcrypt
from database import SessionLocal
import models

def crear_admin():
    db = SessionLocal()
    email_admin = "admin@biomant.com"
    password_admin = "123456" 
    
    usuario = db.query(models.Usuario).filter(models.Usuario.email == email_admin).first()
    
    if not usuario:
        hashed = bcrypt.hashpw(password_admin.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        nuevo_admin = models.Usuario(
            nombre_completo="Administrador Principal",
            email=email_admin,
            password_hash=hashed,
            rol="super_admin",
            activo=True
        )
        db.add(nuevo_admin)
        db.commit()
        print(f"¡Usuario {email_admin} creado con éxito!")
    else:
        print("El usuario ya existe.")
    
    db.close()

if __name__ == "__main__":
    crear_admin()