from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'clave_secreta_super_segura'  # Necesario para manejar sesiones

PASSWORD_STAFF = "1234"  # La contraseña para que el personal pueda ingresar

def consultar_db(query, args=(), one=False):
    conn = sqlite3.connect('evento.db')
    cursor = conn.cursor()
    cursor.execute(query, args)
    rv = cursor.fetchall()
    conn.commit()
    conn.close()
    return (rv[0] if rv else None) if one else rv

@app.route('/')
def inicio():
    if not session.get('logeado'):
        return redirect(url_for('login'))
    return render_template('escanear.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form.get('password')
        if password == PASSWORD_STAFF:
            session['logeado'] = True
            return redirect(url_for('inicio'))
        else:
            return render_template('login.html', error="Contraseña incorrecta")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logeado', None)
    return redirect(url_for('login'))

# API que llama el celular cuando escanea un código
@app.route('/api/validar', methods=['POST'])
def validar_qr():
    if not session.get('logeado'):
        return jsonify({'status': 'error', 'mensaje': 'No autorizado'}), 401

    datos = request.get_json()
    codigo_id = datos.get('codigo_id')

    # Buscar boleto en BDD
    boleto = consultar_db("SELECT estado FROM boletos WHERE id = ?", (codigo_id,), one=True)

    if not boleto:
        return jsonify({'status': 'no_existe', 'mensaje': '❌ Código no encontrado en el sistema'})

    estado_actual = boleto[0]

    if estado_actual == 'DISPONIBLE':
        # Cambiar a USADO
        ahora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        consultar_db("UPDATE boletos SET estado = 'USADO', fecha_uso = ? WHERE id = ?", (ahora, codigo_id))
        return jsonify({'status': 'exito', 'mensaje': f'✅ ¡ACCESO PERMITIDO! Boleto {codigo_id}'})
    else:
        return jsonify({'status': 'usado', 'mensaje': f'⚠️ ¡ALERTA! El boleto {codigo_id} YA FUE USADO'})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)