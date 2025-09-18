from urllib import response
from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer
import httpx
import jwt
import os
from dotenv import load_dotenv
import redis
import json


load_dotenv()  # Cargar variables de entorno desde el archivo .env
app = FastAPI()

# Para manejar la autenticación del token en los encabezados
''' Le indica a FastAPI que la aplicación usará un 
token de portador (Bearer Token) para la autenticación '''

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = "HS256"  # Algoritmo de encriptación para firmar los tokens JWT

# URLs de los microservicios internos
USERS_SERVICE_URL = "http://usuarios:8000"
PRODUCTS_SERVICE_URL = "http://productos:8000"
ORDERS_SERVICE_URL = "http://pedidos:8000"

'''Funcion que otros endpoints pueden usar. 
Su trabajo es recibir un token JWT, validar su autenticidad, 
y extraer la información del usuario para que el 
endpoint pueda usarla de forma segura.'''

def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar el token",
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role")
        if username is None or role is None:
            raise credentials_exception
        return {"username": username, "role": role}
    except jwt.PyJWTError:
        raise credentials_exception

# REDIS, base de datos en memoria para caché
# Configuración de Redis desde variables de entorno   

REDIS_HOST = os.getenv("REDIS_HOST")
REDIS_PORT = int(os.getenv("REDIS_PORT"))
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT) # se crea una insancia del cliente de Redis

# --- Endpoints para la autenticación (redireccionan a usuarios) ---

@app.post("/api/register")  
async def register(request: Request): # recibe el request del cliente
                                     # reenvía la solicitud al microservicio de usuarios
    async with httpx.AsyncClient() as client:  # crea un cliente HTTP asíncrono
        response = await client.post(f"{USERS_SERVICE_URL}/register/", json=await request.json())  # reenvía la solicitud POST al microservicio de usuarios con el cuerpo JSON
        return response.json()

@app.post("/api/token")
async def login (request: Request): # recibe el request del cliente 
                                    # reenvía la solicitud al microservicio de usuarios
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{USERS_SERVICE_URL}/token/", data=await request.form()) # reenvía la solicitud POST al microservicio de usuarios con los datos del formulario
        return response.json()  #respuesta es un JSON con access_token

# --- Endpoints para productos (protegidos con JWT) ---

@app.post("/api/products/create")
async def create_product(request: Request):
    
    try:
        data = await request.json()
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Cuerpo de la petición no es un JSON válido")
    
    # Creamos un nuevo diccionario de encabezados con solo los necesarios
    headers = {
        "Content-Type": "application/json",
        "Authorization": request.headers.get("Authorization")
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{PRODUCTS_SERVICE_URL}/products",
            json=data,
            headers=headers
        )
        response.raise_for_status() # Lanza un error si la respuesta HTTP es 4xx o 5xx
        redis_client.delete("all_products")  # Invalidar caché
        return response.json() # Devolvemos la respuesta del microservicio de productos

@app.get("/api/products/all")
async def get_all_products():
    
    cache_key = "all_products" # se define una clave unica para identificar los datos en la redis
    
    # Intenta obtener los datos del caché de Redis usando la clave "all_products"
    # Si los datos existen redis lo devolvera como una cadena de bytes.
    # Si no existe devuelve none
    cached_data = redis_client.get(cache_key)
    
    if cached_data:
        # Si los datos están en el caché, los devuelve inmediatamente
        print("Datos obtenidos del caché de Redis.")
        return json.loads(cached_data) # loads convierte la cadena de bytes JSON a un objeto de python

    # Si los datos no están en el caché, hace la solicitud al microservicio
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{PRODUCTS_SERVICE_URL}/get/products")
        
    products_data = response.json()
    
    # Almacena los datos en el caché de Redis con un tiempo de expiración
    # (por ejemplo, 3600 segundos = 1 hora)
    redis_client.setex(cache_key, 3600, json.dumps(products_data))
    
    print("Datos obtenidos del microservicio y guardados en el caché.")
    return products_data

@app.delete("/api/products/{id}")
async def delete_product(id: int, request: Request):
    headers = {
        "Content-Type": "application/json",
        "Authorization": request.headers.get("Authorization")
    }

    async with httpx.AsyncClient() as client:
        response = await client.delete(
            f"{PRODUCTS_SERVICE_URL}/products/{id}",
            headers=headers
        )
        response.raise_for_status()
        redis_client.delete("all_products")  # Invalidar caché
        return response.json()

@app.put("/api/products/update/{id}")
async def update_product(id: int, request: Request):
    
    try:
        data = await request.json()
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Cuerpo de la petición no es un JSON válido")
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": request.headers.get("Authorization")
    }

    async with httpx.AsyncClient() as client:
        response = await client.put(
            f"{PRODUCTS_SERVICE_URL}/products/update/{id}",
            json=data,
            headers=headers
        )

        if response.status_code >= 400:
            return JSONResponse(
                status_code=response.status_code,
                content=response.json()
            )

        redis_client.delete("all_products")  # Invalidar caché

        return response.json()

@app.post("/api/orders/create")
async def new_order(request: Request, user: dict = Depends(get_current_user)):
    
    try:
        data = await request.json()
        print("Datos recibidos en Gateway:", data)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Cuerpo de la petición no es un JSON válido")
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": request.headers.get("Authorization")
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{ORDERS_SERVICE_URL}/orders/create",
            json=data,
            headers=headers
        )
        print("📤 Datos enviados al microservicio pedidos:", data)
        print("📥 Respuesta cruda de pedidos:", response.text)

        if response.status_code != 200:
            # devolvemos el detalle tal cual
            raise HTTPException(status_code=response.status_code, detail=response.text)
        
        return response.json()

# Puedes agregar más rutas para usuarios y pedidos de la misma forma