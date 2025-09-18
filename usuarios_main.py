import os
import bcrypt
from datetime import datetime, timedelta
import jwt
from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from database import create_tables, get_db
from models import User as UserModel
from schemas import UserCreate, UserLogin, Token
from fastapi.security import OAuth2PasswordRequestForm


create_tables()

app = FastAPI()

# Clave secreta para JWT
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = "HS256"

# Hash de la contraseña
def hash_password(password: str):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

# Verificar la contraseña si coincide con el hash almacenado
def verify_password(plain_password: str, hashed_password: str):
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

# Crear token JWT
def create_access_token(data: dict, expires_delta: timedelta | None = None): # cantidad de tiempo que dura el token

    # preparacion de los datos del token
    to_encode = data.copy() # hace una copia del diccionario data

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)

    to_encode.update({"exp": expire})  # agrega la fecha de expiracion al diccionario
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    return encoded_jwt

# --- Endpoints ---
@app.post("/register/", response_model=Token) # response_model es el esquema de respuesta que se espera par la interfaz grafica de swagger de fastapi
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    # 1. Verifica si el usuario ya existe
    db_user = db.query(UserModel).filter(UserModel.username == user.username).first()
    
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El nombre de usuario ya está registrado."
        )

    # 2. Si no existe, procede a crear el nuevo usuario
    db_user = UserModel(
        username=user.username,
        hashed_password=hash_password(user.password),
        role=user.role
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    access_token = create_access_token(
        data={"sub": db_user.username, "role": db_user.role}
    )
    return {"access_token": access_token, "token_type": "bearer"}

# OAuth2PasswordRequestForm es una clase especial de FastAPI para manejar formularios de login
# El usuario envia su username y password en un formulario
# Depends le dice a FastAPI que inyecte el formulario en la funcion
# los empaqueta en un objeto form_data

@app.post("/token/", response_model=Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    
    db_user = db.query(UserModel).filter(UserModel.username == form_data.username).first()

    if not db_user or not verify_password(form_data.password, db_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas"
        )
    access_token = create_access_token(
        data={"sub": db_user.username, "role": db_user.role}
    )
    return {"access_token": access_token, "token_type": "bearer"}