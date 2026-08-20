import os
import random
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

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "evento.db")


def inicializar_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS boletos (
            id TEXT PRIMARY KEY,
            estado TEXT NOT NULL
        )
    """
    )
    conn.commit()
    conn.close()


inicializar_db()


# --- VISTA PÚBLICA (PARTIDO Y VENTA) ---
@app.route("/")
def pagina_partido():
    return render_template("index.html")


@app.route("/api/comprar_boleto", methods=["POST"])
def comprar_boleto():
    try:
        datos = request.get_json(silent=True) or {}
        nombre = datos.get("nombre", "").strip()
        cedula = datos.get("cedula", "").strip()

        if not nombre or not cedula:
            return (
                jsonify(
                    {
                        "status": "error",
                        "mensaje": "Por favor ingresa nombre y cédula.",
                    }
                ),
                400,
            )

        codigo_nuevo = f"CUE-{random.randint(100000, 999999)}"

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO boletos (id, estado) VALUES (?, 'DISPONIBLE')",
            (codigo_nuevo,),
        )
        conn.commit()
        conn.close()

        return jsonify({"status": "exito", "codigo": codigo_nuevo})

    except Exception as e:
        return (
            jsonify(
                {"status": "error", "mensaje": f"Error en servidor: {str(e)}"}
            ),
            500,
        )


# --- SISTEMA DE ADMINISTRACIÓN Y ESCÁNER ---
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = request.form.get("usuario")
        password = request.form.get("password")
        # Credenciales de acceso simples
        if usuario == "admin1" and password == "0987":
            session["usuario"] = usuario
            return redirect(url_for("escanear"))
        return render_template("login.html", error="Credenciales incorrectas")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.pop("usuario", None)
    return redirect(url_for("login"))


@app.route("/escanear")
def escanear():
    if "usuario" not in session:
        return redirect(url_for("login"))
    return render_template("escanear.html")


@app.route("/reporte")
def reporte():
    if "usuario" not in session:
        return redirect(url_for("login"))

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, estado FROM boletos")
    boletos = cursor.fetchall()
    conn.close()

    total = len(boletos)
    usados = sum(1 for b in boletos if b[1] == "USADO")
    disponibles = total - usados

    return render_template(
        "reporte.html",
        boletos=boletos,
        total=total,
        usados=usados,
        disponibles=disponibles,
    )


@app.route("/api/validar", methods=["POST"])
def validar_qr():
    if "usuario" not in session:
        return jsonify(
            {"status": "error", "mensaje": "Sesión expirada. Inicie sesión."}
        )

    datos = request.get_json(silent=True) or {}
    codigo_qr = datos.get("codigo", "").strip()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, estado FROM boletos WHERE id = ?", (codigo_qr,)
    )
    resultado = cursor.fetchone()

    if not resultado:
        conn.close()
        return jsonify(
            {
                "status": "invalid",
                "titulo": "⛔ CÓDIGO NO ENCONTRADO",
                "mensaje": f"El código '{codigo_qr}' no existe.",
            }
        )

    boleto_id, estado = resultado

    if estado == "USADO":
        conn.close()
        return jsonify(
            {
                "status": "warning",
                "titulo": "🚫 INGRESO DENEGADO",
                "mensaje": f"¡ALERTA! El boleto #{boleto_id} YA FUE UTILIZADO.",
            }
        )

    cursor.execute(
        "UPDATE boletos SET estado = 'USADO' WHERE id = ?", (boleto_id,)
    )
    conn.commit()
    conn.close()

    return jsonify(
        {
            "status": "valid",
            "titulo": "🎉 ¡INGRESO PERMITIDO!",
            "mensaje": f"Boleto #{boleto_id} verificado con éxito.",
        }
    )


if __name__ == "__main__":
    app.run(debug=True)