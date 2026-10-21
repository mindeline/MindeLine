#!/bin/bash

# 1. Iniciar la API de WhatsApp en segundo plano (puerto 8000)
uvicorn whatsapp_app:app --host 0.0.0.0 --port 8000 &

# 2. Iniciar Streamlit en el puerto principal asignado por Render
streamlit run app.py --server.port $PORT --server.address 0.0.0.0