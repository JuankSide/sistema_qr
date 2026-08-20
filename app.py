import sqlite3
from flask import (
    Flask,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

app = Flask(__name__)
app.secret_key = "clave_secreta_sistema_qr"
DB_PATH = "evento.db"

USUARIO_VALIDO = "admin"
CLAVE_VALIDA = "1234"


@app.route("/")
def home():
    if "usuario" in session:
        return redirect(url_for("escanear"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        usuario = request.form.get("usuario")
        clave = request.form.get("clave")

        if usuario == USUARIO_VALIDO and clave == CLAVE_VALIDA:
            session["usuario"] = usuario
            return redirect(url_for("escanear"))
        else:
            error = "❌ Usuario o contraseña incorrectos."

    return render_template("login.html", error=error)


@app.route("/escanear")
def escanear():
    if "usuario" not in session:
        return redirect(url_for("login"))
    return render_template("escanear.html")


@app.route("/logout")
def logout():
    session.pop("usuario", None)
    return redirect(url_for("login"))


# Reemplaza la función validar_qr en tu app.py con esta versión mejorada

@app.route("/api/validar", methods=["POST"])
def validar_qr():
    if "usuario" not in session:
        return jsonify({"status": "error", "mensaje": "⚠️ Sesión expirada. Inicie sesión nuevamente."})

    datos = request.get_json()
    codigo_qr = datos.get("codigo", "").strip()

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("SELECT id, estado FROM boletos WHERE id = ?", (codigo_qr,))
        resultado = cursor.fetchone()

        if not resultado:
            conn.close()
            return jsonify({
                "status": "invalid",
                "titulo": "⛔ CÓDIGO NO ENCONTRADO",
                "mensaje": f"El código '{codigo_qr}' no existe en el sistema."
            })

        boleto_id, estado = resultado

        if estado == "USADO":
            conn.close()
            return jsonify({
                "status": "warning",
                "titulo": "🚫 INGRESO DENEGADO",
                "mensaje": f"¡ALERTA! El boleto #{boleto_id} YA FUE UTILIZADO previamente."
            })

        # Marcar como usado
        cursor.execute(
            "UPDATE boletos SET estado = 'USADO', fecha_uso = CURRENT_TIMESTAMP WHERE id = ?",
            (boleto_id,),
        )
        conn.commit()
        conn.close()

        return jsonify({
            "status": "valid",
            "titulo": "🎉 ¡INGRESO PERMITIDO!",
            "mensaje": f"Boleto #{boleto_id} verificado con éxito. Pase adelante."
        })

    except sqlite3.Error as e:
        return jsonify({"status": "error", "titulo": "❌ ERROR", "mensaje": f"Error de DB: {e}"})

@app.route("/reporte")
def reporte():
    if "usuario" not in session:
        return redirect(url_for("login"))

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Contar disponibles y usados
    cursor.execute("SELECT COUNT(*) FROM boletos WHERE estado = 'DISPONIBLE'")
    disponibles = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM boletos WHERE estado = 'USADO'")
    usados = cursor.fetchone()[0]

    total = disponibles + usados

    # Obtener lista de los boletos ya ingresados (los más recientes primero)
    cursor.execute(
        "SELECT id, fecha_uso FROM boletos WHERE estado = 'USADO' ORDER BY fecha_uso DESC"
    )
    lista_usados = cursor.fetchall()

    conn.close()

    return render_template(
        "reporte.html",
        total=total,
        disponibles=disponibles,
        usados=usados,
        lista_usados=lista_usados,
    )
@app.route("/reactivar/<codigo_id>")
def reactivar_boleto(codigo_id):
    if "usuario" not in session:
        return redirect(url_for("login"))

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE boletos SET estado = 'DISPONIBLE', fecha_uso = NULL WHERE id = ?",
        (codigo_id,),
    )
    conn.commit()
    conn.close()

    return redirect(url_for("reporte"))
# --- NUEVAS RUTAS PARA LA API DEL PANEL DE ADMINISTRACIÓN ---

@app.route("/api/resumen", methods=["GET"])
def api_resumen():
    if "usuario" not in session:
        return jsonify({"error": "No autorizado"}), 401

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM boletos WHERE estado = 'DISPONIBLE'")
    disponibles = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM boletos WHERE estado = 'USADO'")
    usados = cursor.fetchone()[0]

    total = disponibles + usados

    cursor.execute("SELECT id FROM boletos WHERE estado = 'USADO' ORDER BY fecha_uso DESC")
    usados_rows = cursor.fetchall()
    lista_usados = [{"codigo": row[0]} for row in usados_rows]

    conn.close()

    return jsonify({
        "total": total,
        "disponibles": disponibles,
        "total_usados": usados,
        "usados": lista_usados
    })

@app.route("/api/reactivar_todos", methods=["GET"])
def reactivar_todos():
    if "usuario" not in session:
        return jsonify({"error": "No autorizado"}), 401

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE boletos SET estado = 'DISPONIBLE', fecha_uso = NULL")
    conn.commit()
    conn.close()

    return jsonify({"mensaje": "🔄 Todos los boletos han sido reactivados a DISPONIBLE."})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
    