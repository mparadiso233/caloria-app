import telebot
import sqlite3
import pandas as pd
from datetime import datetime
import os

# --- CONFIGURACIÓN ---
# Reemplazar con el token que te de BotFather
API_TOKEN = 'TU_TOKEN_ACA'
bot = telebot.TeleBot(API_TOKEN)
DB_NAME = 'gastos.db'

# --- BASE DE DATOS ---
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS gastos
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  fecha TEXT,
                  descripcion TEXT,
                  monto REAL,
                  categoria TEXT)''')
    conn.commit()
    conn.close()

# --- LÓGICA DE PROCESAMIENTO ---
def parse_expense(text):
    """Intenta extraer descripción y monto de un texto simple"""
    parts = text.split()
    if len(parts) < 2:
        return None, None
    
    # Buscamos el monto (el que sea número)
    monto = None
    desc_parts = []
    
    for part in parts:
        try:
            # Reemplazar coma por punto para montos
            val = float(part.replace(',', '.'))
            monto = val
        except ValueError:
            desc_parts.append(part)
    
    desc = " ".join(desc_parts)
    return desc, monto

# --- COMANDOS DEL BOT ---
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "¡Hola Mati! Soy GastoIA. 💸\n\nMandame algo como 'Pizza 5000' o 'Nafta 12000' y lo anoto.\nUsá /stats para ver el resumen.")

@bot.message_handler(commands=['stats'])
def show_stats(message):
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM gastos", conn)
    conn.close()
    
    if df.empty:
        bot.reply_to(message, "No hay gastos anotados todavía.")
        return
    
    total = df['monto'].sum()
    resumen = df.groupby('categoria')['monto'].sum().to_dict()
    
    text = f"📊 *Resumen Total: ${total:,.2f}*\n\n"
    for cat, monto in resumen.items():
        text += f"• {cat}: ${monto:,.2f}\n"
    
    bot.reply_to(message, text, parse_mode='Markdown')

@bot.message_handler(func=lambda message: True)
def echo_all(message):
    desc, monto = parse_expense(message.text)
    
    if monto is not None:
        fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # Por ahora categoría simple, después le metemos IA
        categoria = "General" 
        
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("INSERT INTO gastos (fecha, descripcion, monto, categoria) VALUES (?, ?, ?, ?)",
                  (fecha, desc, monto, categoria))
        conn.commit()
        conn.close()
        
        bot.reply_to(message, f"✅ Anotado: *{desc}* por *${monto:,.2f}* en {categoria}", parse_mode='Markdown')
    else:
        bot.reply_to(message, "No entendí el monto. Escribí algo como 'Super 4500'.")

# --- INICIO ---
if __name__ == "__main__":
    print("Bot GastoIA iniciado...")
    init_db()
    bot.infinity_polling()
