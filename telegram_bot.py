import telebot
from telebot import types
import psycopg2
from psycopg2.extras import DictCursor
from datetime import datetime
import pandas as pd
import google.generativeai as genai
import json
import matplotlib.pyplot as plt
import io
import os

# --- CONFIGURACIÓN ---
# Usamos variables de entorno para mayor seguridad en la nube
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "8500038048:AAHI0EeUZ09G2dcuehmhAiCBCDJR34Lm6MY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "AIzaSyAmvBqs_AFln-c-hyRX0H8TXxxOD3eSCfI")
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://postgres:Popopopo23po23@db.jfonixhzdjzogoqqkmkz.supabase.co:5432/postgres")

bot = telebot.TeleBot(TELEGRAM_TOKEN, threaded=True)
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

def get_db_connection():
    return psycopg2.connect(DATABASE_URL, sslmode='require')

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    # Tabla de Gastos
    c.execute('''CREATE TABLE IF NOT EXISTS gastos (
                  id SERIAL PRIMARY KEY,
                  fecha TIMESTAMP,
                  descripcion TEXT,
                  monto NUMERIC,
                  categoria TEXT,
                  metodo_pago TEXT,
                  usuario TEXT)''')
    # Tabla de Perfiles
    c.execute('''CREATE TABLE IF NOT EXISTS perfiles (
                  usuario TEXT PRIMARY KEY,
                  nombre TEXT)''')
    # Tabla de Categorías
    c.execute('''CREATE TABLE IF NOT EXISTS categorias (
                  id SERIAL PRIMARY KEY,
                  nombre TEXT UNIQUE)''')
    # Tabla de Métodos de Pago
    c.execute('''CREATE TABLE IF NOT EXISTS metodos_pago (
                  id SERIAL PRIMARY KEY,
                  nombre TEXT UNIQUE)''')
    
    # Valores por defecto
    cats = ["Auto", "Servicios", "Super", "Delivery", "Malbi y Chiquito", "Otros"]
    for cat in cats:
        c.execute("INSERT INTO categorias (nombre) VALUES (%s) ON CONFLICT DO NOTHING", (cat,))
    
    pags = ["Transferencia", "Trajeta Ciudad Mati", "Tarjeta Santander Cimi"]
    for pag in pags:
        c.execute("INSERT INTO metodos_pago (nombre) VALUES (%s) ON CONFLICT DO NOTHING", (pag,))
        
    conn.commit()
    conn.close()

def main_menu():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add('📊 Hoy', '📅 Rango', '📈 Gráfico', '📝 Detalle', '📂 Categorías', '📥 Excel', '⚙️ Configuración')
    return markup

# --- MANEJADORES ---
@bot.message_handler(commands=['start', 'reset'])
def start(message):
    init_db()
    user_id = str(message.from_user.id)
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT nombre FROM perfiles WHERE usuario = %s", (user_id,))
    res = c.fetchone()
    conn.close()
    if not res:
        msg = bot.send_message(message.chat.id, "¡Hola! Soy GastoIA. 🤖 ¿Cómo te llamás?")
        bot.register_next_step_handler(msg, save_name)
    else:
        bot.send_message(message.chat.id, f"¡Hola, {res[0]}!", reply_markup=main_menu())

def save_name(message):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("INSERT INTO perfiles (usuario, nombre) VALUES (%s, %s) ON CONFLICT (usuario) DO UPDATE SET nombre = EXCLUDED.nombre", 
              (str(message.from_user.id), message.text))
    conn.commit()
    conn.close()
    bot.send_message(message.chat.id, f"¡Bienvenido {message.text}!", reply_markup=main_menu())

@bot.message_handler(func=lambda m: m.text == '⚙️ Configuración')
def config_menu(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton("➕ Categoría", callback_data="add_cat"),
               types.InlineKeyboardButton("❌ Categoría", callback_data="list_del_cat"),
               types.InlineKeyboardButton("➕ Método Pago", callback_data="add_pay"),
               types.InlineKeyboardButton("❌ Método Pago", callback_data="list_del_pay"))
    bot.send_message(message.chat.id, "⚙️ *Configuración*", reply_markup=markup, parse_mode='Markdown')

@bot.message_handler(func=lambda m: True)
def handle_text(message):
    if message.text in ['📊 Hoy', '📅 Rango', '📈 Gráfico', '📝 Detalle', '📂 Categorías', '📥 Excel', '⚙️ Configuración']:
        if message.text == '📊 Hoy': return show_resumen(message)
        if message.text == '📅 Rango': return ask_range(message)
        if message.text == '📈 Gráfico': return send_chart(message)
        if message.text == '📝 Detalle': return res_detalle(message)
        if message.text == '📂 Categorías': return res_cat(message)
        if message.text == '📥 Excel': return export_excel(message)
        if message.text == '⚙️ Configuración': return config_menu(message)
        return

    # Parsing flexible
    clean = message.text.replace('$', '').replace('.', '').replace(',', '.')
    parts = clean.split()
    monto = None
    for p in parts:
        try: monto = float(p); break
        except: pass
    
    if monto:
        try:
            desc = message.text.replace(str(int(monto)), '').strip() or "Gasto"
            conn = get_db_connection()
            c = conn.cursor()
            c.execute("INSERT INTO gastos (fecha, descripcion, monto, categoria, metodo_pago, usuario) VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
                      (datetime.now(), desc, monto, "Sin cat", "Sin pago", str(message.from_user.id)))
            g_id = c.fetchone()[0]
            c.execute("SELECT nombre FROM categorias")
            cats = [r[0] for r in c.fetchall()]
            conn.commit()
            conn.close()
            
            markup = types.InlineKeyboardMarkup(row_width=2)
            markup.add(*[types.InlineKeyboardButton(str(cat), callback_data=f"cat_{g_id}_{cat}") for cat in cats])
            bot.send_message(message.chat.id, f"✅ *{desc}* (${monto:,.2f})\n📂 Elegí Categoría:", reply_markup=markup, parse_mode='Markdown')
        except Exception as e: bot.reply_to(message, f"❌ Error: {e}")
    else: bot.reply_to(message, "No encontré el monto.")

@bot.callback_query_handler(func=lambda call: True)
def handle_all_callbacks(call):
    conn = get_db_connection()
    c = conn.cursor()
    try:
        if call.data.startswith('cat_'):
            _, g_id, val = call.data.split('_')
            c.execute("UPDATE gastos SET categoria = %s WHERE id = %s", (val, g_id))
            conn.commit()
            c.execute("SELECT nombre FROM metodos_pago")
            btns = [types.InlineKeyboardButton(str(m[0]), callback_data=f"pay_{g_id}_{m[0]}") for m in c.fetchall()]
            bot.edit_message_text(f"📂 {val}\n💳 Elegí Método de Pago:", call.message.chat.id, call.message.message_id, reply_markup=types.InlineKeyboardMarkup(row_width=2).add(*btns))
        
        elif call.data.startswith('pay_'):
            _, g_id, val = call.data.split('_')
            c.execute("UPDATE gastos SET metodo_pago = %s WHERE id = %s", (val, g_id))
            conn.commit()
            bot.edit_message_text(f"✅ Gasto guardado con éxito.", call.message.chat.id, call.message.message_id)

        elif call.data.startswith('del_'):
            g_id = call.data.split('_')[1]
            c.execute("DELETE FROM gastos WHERE id = %s", (g_id,))
            conn.commit()
            bot.edit_message_text("🗑️ Eliminado.", call.message.chat.id, call.message.message_id)

        elif call.data == "add_cat":
            msg = bot.send_message(call.message.chat.id, "Escribí la nueva Categoría:")
            bot.register_next_step_handler(msg, lambda m: save_config_item(m, "categorias"))

        elif call.data == "list_del_cat":
            c.execute("SELECT nombre FROM categorias")
            btns = [types.InlineKeyboardButton(r[0], callback_data=f"delcat_{r[0]}") for r in c.fetchall()]
            bot.edit_message_text("Eliminar categoría:", call.message.chat.id, call.message.message_id, reply_markup=types.InlineKeyboardMarkup().add(*btns))

        elif call.data.startswith("delcat_"):
            val = call.data.split('_')[1]
            c.execute("DELETE FROM categorias WHERE nombre = %s", (val,))
            conn.commit()
            bot.send_message(call.message.chat.id, f"✅ '{val}' eliminada.")

    except Exception as e: bot.send_message(call.message.chat.id, f"❌ Error: {e}")
    finally: conn.close()

def save_config_item(message, table):
    conn = get_db_connection()
    try:
        c = conn.cursor()
        c.execute(f"INSERT INTO {table} (nombre) VALUES (%s)", (message.text,))
        conn.commit()
        bot.send_message(message.chat.id, "✅ Guardado correctamente.")
    except: bot.send_message(message.chat.id, "❌ Error o ya existe.")
    conn.close()

# --- REPORTE Y RANGOS ---
def show_resumen(message):
    conn = get_db_connection()
    hoy = datetime.now().strftime("%Y-%m-%d")
    df = pd.read_sql_query(f"SELECT monto FROM gastos WHERE fecha >= '{hoy} 00:00:00'", conn)
    conn.close()
    total = df['monto'].sum() if not df.empty else 0
    bot.send_message(message.chat.id, f"📊 *Total de Hoy:* ${total:,.2f}", parse_mode='Markdown')

def ask_range(message):
    msg = bot.send_message(message.chat.id, "📅 *Resumen por Rango*\n\nEscribí (ej: `21/04 al 20/05`) o `21 al 20`:", parse_mode='Markdown')
    bot.register_next_step_handler(msg, process_range_step)

def process_range_step(message):
    text = message.text.lower().strip()
    ahora = datetime.now()
    try:
        parts = text.split(" al ")
        def parse_date(d_str, is_end=False):
            d_parts = d_str.strip().split("/")
            day = int(d_parts[0])
            month = int(d_parts[1]) if len(d_parts) > 1 else ahora.month
            year = ahora.year
            if not is_end and day > ahora.day and len(d_parts) == 1: month -= 1
            return datetime(year, month, day)
        f_inicio = parse_date(parts[0])
        f_fin = parse_date(parts[1], is_end=True).replace(hour=23, minute=59, second=59)
        conn = get_db_connection()
        df = pd.read_sql_query("SELECT monto FROM gastos WHERE fecha >= %s AND fecha <= %s", conn, params=(f_inicio, f_fin))
        conn.close()
        total = df['monto'].sum() if not df.empty else 0
        bot.send_message(message.chat.id, f"✅ *Resumen:* {f_inicio.strftime('%d/%m')} al {f_fin.strftime('%d/%m')}\n💰 *Total:* ${total:,.2f}", parse_mode='Markdown')
    except: bot.reply_to(message, "❌ Error. Usá: `DD/MM al DD/MM`")

def send_chart(message):
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT categoria, SUM(monto) as total FROM gastos GROUP BY categoria", conn)
    conn.close()
    if df.empty: return bot.reply_to(message, "Sin datos.")
    plt.figure(figsize=(8, 6))
    plt.pie(df['total'], labels=df['categoria'], autopct='%1.1f%%', colors=plt.get_cmap('Pastel1').colors)
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0); plt.close()
    bot.send_photo(message.chat.id, buf)

def res_detalle(message):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT id, descripcion, monto, categoria, metodo_pago FROM gastos ORDER BY id DESC LIMIT 5")
    for r in c.fetchall():
        markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("❌ Borrar", callback_data=f"del_{r[0]}"))
        bot.send_message(message.chat.id, f"📝 {r[1]} - ${r[2]}\n📂 {r[3]} | 💳 {r[4]}", reply_markup=markup)
    conn.close()

def res_cat(message):
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT categoria, SUM(monto) as total FROM gastos GROUP BY categoria", conn)
    conn.close()
    texto = "📂 *Por Categoría:*\n" + "\n".join([f"• {r['categoria']}: ${r['total']:,.2f}" for _, r in df.iterrows()])
    bot.send_message(message.chat.id, texto, parse_mode='Markdown')

def export_excel(message):
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT g.fecha, g.descripcion, g.monto, g.categoria, g.metodo_pago, p.nombre as usuario FROM gastos g LEFT JOIN perfiles p ON g.usuario = p.usuario", conn)
    conn.close()
    path = "resumen_gastos.xlsx"
    df.to_excel(path, index=False)
    with open(path, 'rb') as f: bot.send_document(message.chat.id, f)
    os.remove(path)

if __name__ == "__main__":
    init_db()
    print("Bot GastoIA Cloud iniciado...")
    bot.infinity_polling()
