import token
import httpx
import json

BASE_URL = "http://localhost:80"  # Asegúrate de que este sea el puerto de tu API Gateway

async def register(username, password, role):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/api/register",
            json={"username": username, "password": password, "role": role}
        )
        print(f"Registro: {response.json()}")

async def login(username, password):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/api/token",
            data={"username": username, "password": password}
        )
        return response.json()

async def get_all_products(token):

    headers = {"Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/api/products/all",
            headers=headers
        )
        print(f"Obtener productos: {response.json()}")

async def send_order(token, order_data):

    headers = {"Authorization": f"Bearer {token}"}

    print(f"\nCreando pedido para el cliente con ID: {order_data['user_id']}...")
    print(f"Datos enviados al servidor: {json.dumps(order_data, indent=2)}")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BASE_URL}/api/orders/create",
                headers=headers,
                json=order_data
            )
            response.raise_for_status()
            print("Pedido creado exitosamente.")
            print("Respuesta:", response.json())
            
    except httpx.HTTPStatusError as e:
        print(f"Error HTTP al crear el pedido: {e.response.status_code}")
    
        try:
            print("Detalle del error:", e.response.json()) 
        except Exception:
            print("Respuesta del servidor:", e.response.text)


    except Exception as e:
        print(f"Error inesperado al crear el pedido: {e}")

async def main():
    # 1. Registrar un usuario (si no existe)
    print("Registrando usuario 'testuser'...")
    await register("testuser", "password123", "user")

    # 2. Iniciar sesión para obtener un token
    print("\nIniciando sesión como 'testuser'...")
    login_response = await login("testuser", "password123")
    token = login_response.get("access_token")
    if not token:
        print("Error al obtener el token. Saliendo.")
        return
    print(f"Token obtenido: {token}")

    # 3. Acceder al endpoint de productos
    print("\nObteniendo todos los productos...")
    await get_all_products(token)

     # 3. Crear un pedido
    # NOTA: Asegúrate de que los IDs existan en tu base de datos
    
    order_data = {
        "user_id": 16,        # Reemplaza con el ID de un cliente existente
        "product_id": 21,     # Reemplaza con el ID de un producto existente
        "quantity": 1,
        "total_price": 240.15
    }
    await send_order(token, order_data)  

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())