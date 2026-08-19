import sqlite3

conn = sqlite3.connect("evento.db")
cursor = conn.cursor()

# CASO A: Reiniciar UN SOLO boleto específico (ejemplo: B001)
boleto_id = "B001"
cursor.execute(
    "UPDATE boletos SET estado = 'DISPONIBLE', fecha_uso = NULL WHERE id = ?",
    (boleto_id,),
)
print(f"✅ Boleto {boleto_id} reactivado.")

# CASO B: Reiniciar TODOS los boletos del evento a la vez
# (Descomenta la línea de abajo si quieres liberar todos de golpazo)
# cursor.execute("UPDATE boletos SET estado = 'DISPONIBLE', fecha_uso = NULL")
# print("🎉 Todos los boletos han sido restablecidos a DISPONIBLE.")

conn.commit()
conn.close()