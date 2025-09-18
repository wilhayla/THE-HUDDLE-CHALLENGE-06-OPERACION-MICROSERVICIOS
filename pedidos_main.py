import os
from fastapi.security import OAuth2PasswordBearer
import jwt
import pika  # para interactuar con RabbitMQ
from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from dotenv import load_dotenv
import json

from database import create_tables, get_db
from models import Order as OrderModel
from schemas import Order, OrderCreate
from typing import Any


create_tables()

app = FastAPI()


SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = "HS256"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

# Dependencia para validar el token JWT
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

# --- Función para publicar en RabbitMQ ---
def publish_to_rabbitmq(message):
    connection = None
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters(host=os.getenv("RABBITMQ_HOST")))
        channel = connection.channel()
        channel.queue_declare(queue='order_queue')
        channel.basic_publish(
            exchange='',
            routing_key='order_queue',
            body=json.dumps(message)
        )
        print(f" [x] Mensaje enviado a RabbitMQ: {message}")
    finally:
        if connection and connection.is_open:
            connection.close()

# --- Endpoints ---

@app.post("/orders/create", response_model=OrderCreate)
def create_order(order: OrderCreate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)) -> Any:

    print(f"Datos recibidos en el microservicio de pedidos: {order.model_dump()}")

    if current_user["role"] != "user":
        raise HTTPException(status_code=403, detail="No tienes permiso para crear pedidos")
    # Aquí puedes agregar lógica para verificar si el usuario tiene permiso
    
    db_order = OrderModel(
        user_id=order.user_id,
        product_id=order.product_id,
        quantity=order.quantity,
        total_price=order.total_price,
        status="pending"
    )
    
    db.add(db_order)
    db.commit()
    db.refresh(db_order)

    print("DB Order después de refresh:", db_order.__dict__)


    # Publica un mensaje en RabbitMQ para que el servicio de productos actualice el stock
    message = {
        "order_id": db_order.id,
        "product_id": order.product_id,
        "quantity": order.quantity
    }
    publish_to_rabbitmq(message)

    print("Pedido guardado en la base de datos:", db_order.__dict__)

    return db_order