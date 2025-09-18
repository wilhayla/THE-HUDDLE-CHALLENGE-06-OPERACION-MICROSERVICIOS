#!/bin/bash

# Este comando espera a que la base de datos esté lista
# Se conecta al host de la base de datos y se asegura de que esté escuchando
echo "Esperando a que la base de datos de PostgreSQL esté lista..."
until pg_isready -h db_usuarios -p 5432 -U postgres; do
  echo "Todavía esperando la base de datos..."
  sleep 2
done

# Este comando ejecuta tu script de Python para crear las tablas
echo "Creando las tablas de la base de datos..."
python database.py

# Este comando inicia tu aplicación principal
echo "Iniciando el servidor de Uvicorn..."
exec uvicorn main:app --host 0.0.0.0 --port 8000