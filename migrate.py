import sqlite3
conn = sqlite3.connect('gastos.db')
c = conn.cursor()
try:
    c.execute('ALTER TABLE gastos ADD COLUMN metodo_pago TEXT')
    print("Columna metodo_pago agregada.")
except Exception as e:
    print(f"Nota: {e}")
conn.commit()
conn.close()
