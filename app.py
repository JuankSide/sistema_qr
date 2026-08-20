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


@app.route("/api/validar", methods=["POST"])
def validar_qr():
    if "usuario" not in session:
        return jsonify(
            {"status": "error", "mensaje": "⚠️ Sesión expirada. Inicie sesión."}
        )

    datos = request.get_json()
    codigo_qr = datos.get("codigo", "").strip()

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Busca el código en la tabla 'boletos'
        cursor.execute(
            "SELECT id, estado FROM boletos WHERE id = ?", (codigo_qr,)
        )
        resultado = cursor.fetchone()

        if not resultado:
            conn.close()
            return jsonify(
                {
                    "status": "error",
                    "mensaje": f"❌ CÓDIGO INVÁLIDO: '{codigo_qr}' no existe.",
                }
            )

        boleto_id, estado = resultado

        if estado == "USADO":
            conn.close()
            return jsonify(
                {
                    "status": "warning",
                    "mensaje": f"⚠️ ALERTA: El boleto {boleto_id} YA FUE UTILIZADO.",
                }
            )

        # Marca como USADO y guarda la fecha y hora de acceso
        cursor.execute(
            "UPDATE boletos SET estado = 'USADO', fecha_uso = CURRENT_TIMESTAMP WHERE id = ?",
            (boleto_id,),
        )
        conn.commit()
        conn.close()

        return jsonify(
            {
                "status": "exito",
                "mensaje": f"✅ ACCESO PERMITIDO: Boleto válido ({boleto_id}).",
            }
        )

    except sqlite3.Error as e:
        return jsonify(
            {"status": "error", "mensaje": f"❌ Error de base de datos: {e}"}
        )

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
    