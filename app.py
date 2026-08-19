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

app = Flask(_name_)
app.secret_key = "clave_secreta_sistema_qr"
DB_PATH = "evento.db"

# Usuario y contraseña para el personal de acceso
USUARIO_VALIDO = "admin"
CLAVE_VALIDA = "1234"


def preparar_base_datos():
    """Asegura que la tabla 'qrs' tenga la columna 'estado'"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "ALTER TABLE qrs ADD COLUMN estado TEXT DEFAULT 'DISPONIBLE'"
        )
        conn.commit()
    except sqlite3.OperationalError:
        pass
    conn.close()


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
    contenido_qr = datos.get("codigo", "").strip()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, estado FROM qrs WHERE contenido = ?", (contenido_qr,)
    )
    resultado = cursor.fetchone()

    if not resultado:
        conn.close()
        return jsonify(
            {
                "status": "error",
                "mensaje": "❌ CÓDIGO INVÁLIDO: No existe en la base de datos.",
            }
        )

    qr_id, estado = resultado

    if estado == "USADO":
        conn.close()
        return jsonify(
            {
                "status": "warning",
                "mensaje": f"⚠️ ALERTA: El boleto ({contenido_qr}) YA FUE UTILIZADO.",
            }
        )

    cursor.execute("UPDATE qrs SET estado = 'USADO' WHERE id = ?", (qr_id,))
    conn.commit()
    conn.close()

    return jsonify(
        {
            "status": "exito",
            "mensaje": f"✅ ACCESO PERMITIDO: Boleto válido ({contenido_qr}).",
        }
    )


if _name_ == "_main_":
    preparar_base_datos()
    app.run(host="0.0.0.0", port=5000, debug=True)