import httpx   # para enviar y recibir solicitudes HTTP de manera asíncrona
import asyncio # para manejar la programación asíncrona
import json

BASE_URL = "http://localhost:80" # URL base del servicio API Gateway

async def register(username, password, role):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/api/register",
            json={"username": username, "password": password, "role": role}
        )
        try:
            return response.json()
        except Exception:
            return {"error": response.text, "status": response.status_code}

'''enviar las credenciales del usuario a la API Gateway y, 
si son correctas, recibir un token JWT para futuras peticiones.'''    

async def login(username, password):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/api/token",
            data={"username": username, "password": password}
        )
        try:
            return response.json()
        except Exception:
            return {"error": response.text, "status": response.status_code}

'''preparar la información y el token de autenticación 
para crear un nuevo producto.'''  

async def create_product(token: str, name: str, price: float, stock: int):

    # preparar de las cabeceras http con el token JWT
    headers = {"Authorization": f"Bearer {token}"}

    # preparar el cuerpo con los datos del producto
    data_payload = {"name": name, "price": price, "stock": stock}

    print("\n--- Enviando petición para crear producto ---")
    print(f"URL: {BASE_URL}/api/products/create")
    print(f"Headers: {headers}")
    print(f"JSON Payload: {data_payload}")
    print("---------------------------------------------")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/api/products/create",
            json=data_payload,
            headers=headers
        )
        print(f"Status code: {response.status_code}")
        
        try:
            data = response.json()
            print(f"Respuesta JSON: {data}")
            return data
        
        except Exception:
            print(f"Respuesta texto plano: {response.text}")
            return {"error": response.text, "status": response.status_code}

async def delete_product(token: str, id: int):

    headers = {"Authorization": f"Bearer {token}"}

    print("\n--- Enviando petición para eliminar producto ---")
    print(f"URL: {BASE_URL}/api/products/{id}")
    print(f"Headers: {headers}")
    print("---------------------------------------------")

    async with httpx.AsyncClient() as client:
        response = await client.delete(
            f"{BASE_URL}/api/products/{id}",
            headers=headers
        )
        print(f"Status code: {response.status_code}")

        try:
            data = response.json()
            print(f"Respuesta JSON: {data}")
            return data

        except Exception:
            print(f"Respuesta texto plano: {response.text}")

async def get_product(token: str):

    headers = {"Authorization": f"Bearer {token}"}

    print("\n--- Enviando petición para obtener producto ---")
    print(f"URL: {BASE_URL}/api/products/all")
    print(f"Headers: {headers}")
    print("---------------------------------------------")
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/api/products/all",
            headers=headers 
        )
        print(f"Status code: {response.status_code}")

        try:
            data = response.json()
            print(f"Respuesta JSON: {data}")
            return data

        except Exception:
            print(f"Respuesta texto plano: {response.text}")
        
async def actualize_product(token: str, id: int, name: str, price: float, stock: int):

    headers = {"Authorization": f"Bearer {token}"}

    data_payload = {"name": name, "price": price, "stock": stock}

    print("\n--- Enviando petición para actualizar producto ---")
    print(f"URL: {BASE_URL}/api/products/update/{id}")
    print(f"Headers: {headers}")
    print(f"JSON Payload: {data_payload}")
    print("---------------------------------------------")
    
    async with httpx.AsyncClient() as client:
        response = await client.put(
            f"{BASE_URL}/api/products/update/{id}",
            json=data_payload,
            headers=headers
        )
        print(f"Status code: {response.status_code}")

        try:
            data = response.json()
            print(f"Respuesta JSON: {data}")
            return data
        except Exception:
            print(f"Respuesta texto plano: {response.text}")

async def main():
    # 1. Registrar un usuario con rol 'admin'
    print("Registrando usuario 'adminuser'...")
    registro = await register("adminuser", "adminpass", "admin")
    print(f"Respuesta de registro: {registro}")


    # 2. Iniciar sesión como administrador
    print("\nIniciando sesión como 'adminuser'...")
    login_response = await login("adminuser", "adminpass")
    print(f"Respuesta de login: {login_response}")

    if "access_token" not in login_response:
        print("Error al obtener el token de administrador. Saliendo.")
        return
    
    admin_token = login_response.get("access_token")
    print(f"Token de administrador obtenido: {admin_token}")

    # 3. Crear un nuevo producto
    #print("\nCreando un nuevo producto...")
    #await create_product(admin_token, "tablet", 240.15, 5)
    #await get_product(admin_token)
    #await delete_product(admin_token, 20)
    await actualize_product(admin_token, 21, "tablet", 240.15, 3)

if __name__ == "__main__":
    asyncio.run(main())
