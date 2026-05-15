from fastapi import FastAPI, Request
import sqlite3
from datetime import datetime, timedelta
import pandas as pd
import uvicorn
import google.generativeai as genai
import base64
import json
import io

app = FastAPI()
DB_NAME = 'gastos.db'

# --- CONFIGURACIÓN DE IA ---
GEMINI_API_KEY = "AIzaSyAmvBqs_AFln-c-hyRX0H8TXxxOD3eSCfI"
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS gastos
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  fecha TEXT,
                  descripcion TEXT,
                  monto REAL,
                  categoria TEXT,
                  usuario TEXT)''')
    conn.commit()
    conn.close()

def process_ticket_with_ai(base64_image):
    """Usa Gemini para extraer datos del ticket"""
    try:
        img_data = base64.b64decode(base64_image)
        prompt = """Analiza esta imagen de un ticket de compra y extrae:
        1. Lugar/Comercio (ej: Coto, Farmacity, Shell)
        2. Monto Total (solo el número)
        3. Categoría (Supermercado, Farmacia, Combustible, Comida, Otro)
        Responde ÚNICAMENTE en formato JSON así: {"lugar": "nombre", "total": 1234.50, "categoria": "tipo"}"""
        
        response = model.generate_content([
            prompt,
            {'mime_type': 'image/jpeg', 'data': img_data}
        ])
        
        # Limpiar la respuesta para obtener el JSON
        res_text = response.text.strip()
        if "```json" in res_text:
            res_text = res_text.split("```json")[1].split("```")[0].strip()
        
        return json.loads(res_text)
    except Exception as e:
        print(f"Error en IA: {e}")
        return None

def parse_expense(text):
    parts = text.split()
    if len(parts) < 2:
        return None, None
    monto = None
    desc_parts = []
    for part in parts:
        try:
            val = float(part.replace(',', '.'))
            monto = val
        except ValueError:
            desc_parts.append(part)
    desc = " ".join(desc_parts)
    return desc, monto

@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    message = data.get("message", "").strip().lower()
    sender = data.get("sender", "Desconocido")
    image_b64 = data.get("image")
    
    # --- LÓGICA DE IMAGEN (OCR) ---
    if image_b64:
        print("> Procesando imagen con Gemini...")
        result = process_ticket_with_ai(image_b64)
        if result:
            desc = result.get("lugar", "Gasto por Foto")
            monto = result.get("total", 0)
            categoria = result.get("categoria", "General")
            
            fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("INSERT INTO gastos (fecha, descripcion, monto, categoria, usuario) VALUES (?, ?, ?, ?, ?)",
                      (fecha, desc, monto, categoria, sender))
            conn.commit()
            conn.close()
            
            return {"status": "success", "response": f"📸 *Ticket Detectado*\n📍 Lugar: {desc}\n💰 Total: ${monto:,.2f}\n📂 Categoría: {categoria}\n✅ Anotado correctamente."}
        else:
            return {"status": "success", "response": "❌ No pude leer bien el ticket. ¿Podrás mandarme una foto más clara o anotarlo a mano?"}

    # --- COMANDOS DE CONSULTA ---
    if message in ["/resumen", "resumen", "total", "detalle"]:
        texto = "📊 *¿Qué detalle querés ver?*\n\n1️⃣ Hoy\n2️⃣ Semana pasada\n3️⃣ Mes pasado\n\n_Respondé con el número._"
        return {"status": "success", "response": texto}

    # --- LÓGICA DE FILTROS POR FECHA ---
    conn = sqlite3.connect(DB_NAME)
    query = "SELECT descripcion, monto, fecha FROM gastos WHERE 1=1"
    hoy_dt = datetime.now()
    filtro_aplicado = False
    titulo = ""

    if message in ["1", "1️⃣", "hoy"]:
        query += f" AND fecha >= '{hoy_dt.strftime('%Y-%m-%d')} 00:00:00'"
        titulo = "📅 *Gastos de Hoy*"
        filtro_aplicado = True
    elif message in ["2", "2️⃣", "semana"]:
        inicio_semana = hoy_dt - timedelta(days=7)
        query += f" AND fecha >= '{inicio_semana.strftime('%Y-%m-%d')} 00:00:00'"
        titulo = "📅 *Gastos de la Semana*"
        filtro_aplicado = True
    elif message in ["3", "3️⃣", "mes"]:
        inicio_mes = hoy_dt.replace(day=1)
        query += f" AND fecha >= '{inicio_mes.strftime('%Y-%m-%d')} 00:00:00'"
        titulo = "📅 *Gastos del Mes*"
        filtro_aplicado = True

    if filtro_aplicado:
        df = pd.read_sql_query(query, conn)
        conn.close()
        if df.empty:
            return {"status": "success", "response": f"{titulo}\n\nNo hay gastos anotados en este periodo. 🏜️"}
        
        total = df['monto'].sum()
        texto = f"{titulo}\n\n"
        for _, row in df.iterrows():
            texto += f"• {row[0]}: ${row[1]:,.2f}\n"
        texto += f"\n💰 *Total:* ${total:,.2f}"
        return {"status": "success", "response": texto}
    
    conn.close()

    # --- LÓGICA DE CARGA MANUAL ---
    desc, monto = parse_expense(message)
    if monto is not None:
        fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        categoria = "General"
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("INSERT INTO gastos (fecha, descripcion, monto, categoria, usuario) VALUES (?, ?, ?, ?, ?)",
                  (fecha, desc, monto, categoria, sender))
        conn.commit()
        conn.close()
        return {"status": "success", "response": f"✅ Anotado para {desc}: *${monto:,.2f}*"}
    
    return {"status": "ignored", "response": "No entendí. Probá con 'GASTO Pizza 500' o mandame una foto del ticket."}

if __name__ == "__main__":
    init_db()
    print("Servidor GastoIA v3 (con Visión) iniciado...")
    uvicorn.run(app, host="0.0.0.0", port=5000)
