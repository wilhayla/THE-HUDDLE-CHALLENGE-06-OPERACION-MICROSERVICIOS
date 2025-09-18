import pika
import os
import json
import logging
import time # Añadir importación de time
import threading
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Product  # Importa el modelo de producto


# Configuración de logging
logging.basicConfig(level=logging.INFO)

# Configuración de la base de datos
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")

# Construye la URL de la base de datos
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"
logging.info(f"Conectando a la base de datos con URL: {DATABASE_URL}")

try:
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
except Exception as e:
    logging.error(f"No se pudo crear el motor de la base de datos: {e}")
    engine = None
    SessionLocal = None


def update_product_stock(order_data: dict):
    """
    Actualiza el stock del producto en la base de datos.
    """
    if SessionLocal is None:
        logging.error("No se pudo conectar a la base de datos. Saltando la actualización del stock.")
        return

    db = SessionLocal()
    try:
        product_id = order_data["id"]
        quantity = order_data["stock"]

        # 1. Obtiene el producto de la base de datos
        product = db.query(Product).filter(Product.id == product_id).first()
        if product:
            # 2. Actualiza el stock
            if product.stock >= quantity:
                product.stock -= quantity
                db.commit()
                logging.info(f"Stock actualizado para el producto ID: {product_id}. Nuevo stock: {product.stock}")
            else:
                logging.warning(f"No hay suficiente stock para el producto ID: {product_id}.")
        else:
            logging.warning(f"Producto con ID {product_id} no encontrado.")
    except Exception as e:
        db.rollback()
        logging.error(f"Error al procesar el mensaje de la orden: {e}")
    finally:
        db.close()

def callback(ch, method, properties, body):
    """
    Función que se llama cada vez que se recibe un mensaje.
    """
    logging.info(f" [x] Mensaje recibido: {body.decode()}")
    order_data = json.loads(body.decode())
    
    # Procesa la orden y actualiza el stock
    update_product_stock(order_data)
    
    # Confirma el procesamiento del mensaje
    ch.basic_ack(delivery_tag=method.delivery_tag)

def start_consumer():
    """
    Se conecta a RabbitMQ y comienza a consumir mensajes.
    """
    retries = 5
    while retries > 0:
        try:
            logging.info("Intentando conectar a RabbitMQ...")
            connection = pika.BlockingConnection(pika.ConnectionParameters(host=os.getenv("RABBITMQ_HOST")))
            channel = connection.channel()

            # Asegura que la cola existe
            channel.queue_declare(queue='order_queue')
            logging.info(' [*] Esperando mensajes. Para salir presiona CTRL+C')

            # Empieza a consumir mensajes de la cola
            channel.basic_consume(
                queue='order_queue', 
                on_message_callback=callback
            )
            
            # Inicia el bucle de consumo. Esto es bloqueante.
            channel.start_consuming()

        except pika.exceptions.AMQPConnectionError as e:
            retries -= 1
            logging.error(f"No se pudo conectar a RabbitMQ: {e}. Reintentando en 5 segundos... (intentos restantes: {retries})")
            time.sleep(5)
        except Exception as e:
            logging.error(f"Error inesperado en el consumidor de RabbitMQ: {e}")
            break

if __name__ == "__main__":
    start_consumer()