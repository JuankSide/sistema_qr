import sqlite3
import os
import qrcode

# 1. Crear/Conectar a la Base de Datos SQLite
conn = sqlite3.connect('evento.db')
cursor = conn.cursor()

cursor.execute('''
    CREATE TABLE IF NOT EXISTS boletos (
        id TEXT PRIMARY KEY,
        estado TEXT DEFAULT 'DISPONIBLE',
        fecha_uso TIMESTAMP
    )
''')

# 2. Crear la carpeta para los códigos QR
os.makedirs('codigos_qr', exist_ok=True)

# 3. Insertar 300 registros y generar las imágenes
print("Generando 300 códigos QR...")
for i in range(1, 3001):
    codigo_id = f"B{i:03d}"  # Genera formato: B001, B002... B300
    
    # Insertar en BDD
    cursor.execute("INSERT OR IGNORE INTO boletos (id, estado) VALUES (?, 'DISPONIBLE')", (codigo_id,))
    
    # Generar la imagen del QR (Contiene SOLO el ID, ej: "B001")
    img = qrcode.make(codigo_id)
    img.save(f'codigos_qr/{codigo_id}.png')

conn.commit()
conn.close()
print("¡Completado! Se creó 'evento.db' y 3000 imágenes en '/codigos_qr'.")