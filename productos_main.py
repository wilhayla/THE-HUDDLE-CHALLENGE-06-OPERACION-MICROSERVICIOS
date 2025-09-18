import os
import threading
from dotenv import load_dotenv
import jwt
from sqlalchemy.orm import Session
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from database import create_tables, get_db
from models import Product as ProductModel
from schemas import Product, ProductCreate, ProductUpdate, ProductBase
from typing import Any, List
import logging
from consumer import start_consumer  # Importa la función del consumidor

logging.basicConfig(level=logging.INFO)

create_tables()  # Aseguramos que las tablas estén creadas

app = FastAPI()  # Instancia de FastAPI

SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = "HS256"

oauth2_scheme = HTTPBearer() # Esquema de seguridad HTTP Bearer. Instancia de HTTPBearer que maneja la autenticación mediante tokens Bearer.
                             # Se utiliza para proteger los endpoints y asegurar que solo usuarios autenticados puedan acceder a ellos.

# Funcionpara autenticar a un usuario a partir de su token JWT
# Extrae el token del encabezado de autorización, lo decodifica y verifica su validez.
# Si el token es válido, devuelve la información del usuario (nombre de usuario y rol).
# extrae el token del encabezado de autorizacion, lo guarda en un objeto credentials

# credentials.credentials contiene el token en sí

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(oauth2_scheme)) -> dict:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar el token",
    )
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])  # Decodifica el token JWT usando la clave secreta y el algoritmo especificado
        username: str = payload.get("sub")
        role: str = payload.get("role")
        if username is None or role is None:
            raise credentials_exception
        return {"username": username, "role": role}
    except jwt.PyJWTError:
        raise credentials_exception

# --- Endpoints ---
@app.post("/products", response_model=Product)
def create_product(product: ProductCreate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)) -> Any:

    logging.info(f"Usuario actual intentando crear producto: {current_user}")
    logging.info(f"Datos del producto recibido: {product}")

    # Solo los administradores pueden crear productos
    if current_user["role"] != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes permisos de administrador")
    
    try:
        try:
         logging.info("Intentando crear ProductModel usando product.model_dump()")
         db_product = ProductModel(**product.model_dump())  # ** desempaqueta el diccionario devuelto por model_dump() en sus pares clave-valor
        except AttributeError:
            logging.info("model_dump() falló, usando product.dict()")
            db_product = ProductModel(**product.dict())

        logging.info("Agregando producto a la base de datos")

        db.add(db_product)
        db.commit()
        db.refresh(db_product)
        logging.info(f"Producto creado exitosamente: {db_product}")
        return db_product
    
    except Exception as e:
        logging.error(f"Error interno al crear el producto: {str(e)}")
        import traceback   # Para imprimir el traceback completo del error
        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=f"Error interno al crear el producto: {str(e)}"
        )
    
@app.get("/get/products", response_model=List[Product])
def get_products(db: Session = Depends(get_db)):
    """
    Obtiene y devuelve una lista de todos los productos de la base de datos.
    
    Este endpoint es el que tu API Gateway está esperando.
    """
    logging.info("Solicitud GET para obtener todos los productos.")
    products = db.query(ProductModel).all()
    return products
    
@app.delete("/products/{id}") 
def delete_product(id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)) -> Any:
    logging.info(f"Usuario actual intentando eliminar producto: {current_user}")

    # Solo los administradores pueden eliminar productos
    if current_user["role"] != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes permisos de administrador")
    
    product = db.query(ProductModel).filter(ProductModel.id == id).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Producto no encontrado")
    
    db.delete(product)
    db.commit()
    logging.info(f"Producto con ID {id} eliminado exitosamente.")
    return {"detail": "Producto eliminado exitosamente"}

@app.put("/products/update/{id}", response_model=Product)
def update_product(id: int, product_data: ProductUpdate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)) -> Any:
    logging.info(f"Usuario actual intentando actualizar producto: {current_user}")
    logging.info(f"Datos del producto recibido para actualización: {product_data}")

    # Solo los administradores pueden actualizar productos
    if current_user["role"] != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes permisos de administrador")

    db_product = db.query(ProductModel).filter(ProductModel.id == id).first()

    if not db_product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Producto no encontrado")
    
    try:
        for key, value in product_data.model_dump().items():
            setattr(db_product, key, value)

        db.commit()
        db.refresh(db_product)
        logging.info(f"Producto actualizado exitosamente: {db_product}")
        return db_product
    
    except Exception as e:
        db.rollback()
        logging.error(f"Error interno al actualizar el producto: {str(e)}")
        import traceback
        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=f"Error interno al actualizar el producto: {str(e)}"
        )
    
# Lanza el consumidor de RabbitMQ en un hilo separado al inicio
@app.lifespan("startup")
def startup_event():
    # Inicia el consumidor en un hilo separado
    consumer_thread = threading.Thread(target=start_consumer)
    consumer_thread.daemon = True
    consumer_thread.start()