from flask import Flask, request, jsonify, session, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "oficina.db"

app = Flask(__name__, static_folder="static", static_url_path="/static")
app.config["SECRET_KEY"] = "troque-esta-chave-por-uma-chave-segura"
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    with get_db() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            name TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            email TEXT DEFAULT '',
            document TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS vehicles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER NOT NULL,
            brand TEXT NOT NULL,
            model TEXT NOT NULL,
            plate TEXT NOT NULL UNIQUE,
            year INTEGER,
            color TEXT DEFAULT '',
            FOREIGN KEY(client_id) REFERENCES clients(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER NOT NULL,
            vehicle_id INTEGER,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            service TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Agendado',
            notes TEXT DEFAULT '',
            FOREIGN KEY(client_id) REFERENCES clients(id) ON DELETE CASCADE,
            FOREIGN KEY(vehicle_id) REFERENCES vehicles(id) ON DELETE SET NULL
        );
        CREATE TABLE IF NOT EXISTS work_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER NOT NULL,
            vehicle_id INTEGER,
            description TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Aberta',
            labor REAL NOT NULL DEFAULT 0,
            parts REAL NOT NULL DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(client_id) REFERENCES clients(id) ON DELETE CASCADE,
            FOREIGN KEY(vehicle_id) REFERENCES vehicles(id) ON DELETE SET NULL
        );
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kind TEXT NOT NULL CHECK(kind IN ('Receita','Despesa')),
            description TEXT NOT NULL,
            amount REAL NOT NULL,
            date TEXT NOT NULL,
            notes TEXT DEFAULT ''
        );
        """)
        user = db.execute("SELECT id FROM users WHERE email = ?", ("admin@autopro.local",)).fetchone()
        if not user:
            db.execute(
                "INSERT INTO users (email, password_hash, name) VALUES (?, ?, ?)",
                ("admin@autopro.local", generate_password_hash("admin123"), "Administrador")
            )


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"error": "Autenticação necessária."}), 401
        return fn(*args, **kwargs)
    return wrapper


def body():
    return request.get_json(silent=True) or {}


def row_dict(row):
    return dict(row) if row else None


@app.route("/")
def home():
    return send_from_directory(BASE_DIR / "static", "index.html")


@app.get("/api/health")
def health():
    return jsonify({"status": "ok", "message": "API AutoPro Garage funcionando"})


@app.post("/api/login")
def login():
    data = body()
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))
    with get_db() as db:
        user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "E-mail ou senha inválidos."}), 401
    session.clear()
    session["user_id"] = user["id"]
    session["user_name"] = user["name"]
    return jsonify({"message": "Login realizado.", "user": {"id": user["id"], "name": user["name"], "email": user["email"]}})


@app.post("/api/logout")
def logout():
    session.clear()
    return jsonify({"message": "Sessão encerrada."})


@app.get("/api/me")
def me():
    if "user_id" not in session:
        return jsonify({"authenticated": False}), 401
    return jsonify({"authenticated": True, "name": session.get("user_name")})


@app.get("/api/dashboard")
@login_required
def dashboard():
    with get_db() as db:
        clients = db.execute("SELECT COUNT(*) n FROM clients").fetchone()["n"]
        vehicles = db.execute("SELECT COUNT(*) n FROM vehicles").fetchone()["n"]
        appointments = db.execute("SELECT COUNT(*) n FROM appointments WHERE status = 'Agendado'").fetchone()["n"]
        orders = db.execute("SELECT COUNT(*) n FROM work_orders WHERE status != 'Concluída'").fetchone()["n"]
        income = db.execute("SELECT COALESCE(SUM(amount),0) n FROM transactions WHERE kind='Receita'").fetchone()["n"]
        expenses = db.execute("SELECT COALESCE(SUM(amount),0) n FROM transactions WHERE kind='Despesa'").fetchone()["n"]
    return jsonify({"clients": clients, "vehicles": vehicles, "appointments": appointments,
                    "open_orders": orders, "income": income, "expenses": expenses,
                    "balance": income - expenses})


# Generic CRUD helpers for straightforward API endpoints.
def list_rows(table, order="id DESC"):
    with get_db() as db:
        rows = db.execute(f"SELECT * FROM {table} ORDER BY {order}").fetchall()
    return jsonify([dict(r) for r in rows])


def delete_row(table, item_id):
    with get_db() as db:
        cur = db.execute(f"DELETE FROM {table} WHERE id = ?", (item_id,))
        if cur.rowcount == 0:
            return jsonify({"error": "Registro não encontrado."}), 404
    return jsonify({"message": "Registro excluído."})


@app.get("/api/clients")
@login_required
def clients_list():
    with get_db() as db:
        rows = db.execute("SELECT * FROM clients ORDER BY name").fetchall()
    return jsonify([dict(r) for r in rows])


@app.post("/api/clients")
@login_required
def clients_create():
    d = body()
    name, phone = str(d.get("name", "")).strip(), str(d.get("phone", "")).strip()
    if not name or not phone:
        return jsonify({"error": "Nome e telefone são obrigatórios."}), 400
    with get_db() as db:
        cur = db.execute("INSERT INTO clients(name, phone, email, document) VALUES(?,?,?,?)",
                         (name, phone, d.get("email", ""), d.get("document", "")))
        item = db.execute("SELECT * FROM clients WHERE id=?", (cur.lastrowid,)).fetchone()
    return jsonify(dict(item)), 201


@app.put("/api/clients/<int:item_id>")
@login_required
def clients_update(item_id):
    d = body()
    with get_db() as db:
        old = db.execute("SELECT * FROM clients WHERE id=?", (item_id,)).fetchone()
        if not old:
            return jsonify({"error": "Cliente não encontrado."}), 404
        values = [d.get(k, old[k]) for k in ("name", "phone", "email", "document")]
        if not str(values[0]).strip() or not str(values[1]).strip():
            return jsonify({"error": "Nome e telefone são obrigatórios."}), 400
        db.execute("UPDATE clients SET name=?, phone=?, email=?, document=? WHERE id=?", (*values, item_id))
        item = db.execute("SELECT * FROM clients WHERE id=?", (item_id,)).fetchone()
    return jsonify(dict(item))


@app.delete("/api/clients/<int:item_id>")
@login_required
def clients_delete(item_id):
    return delete_row("clients", item_id)


@app.get("/api/vehicles")
@login_required
def vehicles_list():
    with get_db() as db:
        rows = db.execute("""SELECT v.*, c.name AS client_name FROM vehicles v
                             JOIN clients c ON c.id=v.client_id ORDER BY v.id DESC""").fetchall()
    return jsonify([dict(r) for r in rows])


@app.post("/api/vehicles")
@login_required
def vehicles_create():
    d = body()
    required = ("client_id", "brand", "model", "plate")
    if any(not str(d.get(k, "")).strip() for k in required):
        return jsonify({"error": "Cliente, marca, modelo e placa são obrigatórios."}), 400
    try:
        with get_db() as db:
            cur = db.execute("INSERT INTO vehicles(client_id,brand,model,plate,year,color) VALUES(?,?,?,?,?,?)",
                             (int(d["client_id"]), d["brand"], d["model"], d["plate"].upper().strip(),
                              d.get("year") or None, d.get("color", "")))
            row = db.execute("""SELECT v.*, c.name AS client_name FROM vehicles v JOIN clients c ON c.id=v.client_id
                                WHERE v.id=?""", (cur.lastrowid,)).fetchone()
        return jsonify(dict(row)), 201
    except sqlite3.IntegrityError:
        return jsonify({"error": "Placa já cadastrada ou cliente inválido."}), 400


@app.delete("/api/vehicles/<int:item_id>")
@login_required
def vehicles_delete(item_id):
    return delete_row("vehicles", item_id)


@app.get("/api/appointments")
@login_required
def appointments_list():
    with get_db() as db:
        rows = db.execute("""SELECT a.*, c.name AS client_name, v.plate AS plate
                             FROM appointments a JOIN clients c ON c.id=a.client_id
                             LEFT JOIN vehicles v ON v.id=a.vehicle_id
                             ORDER BY a.date DESC, a.time DESC""").fetchall()
    return jsonify([dict(r) for r in rows])


@app.post("/api/appointments")
@login_required
def appointments_create():
    d = body()
    required = ("client_id", "date", "time", "service")
    if any(not str(d.get(k, "")).strip() for k in required):
        return jsonify({"error": "Cliente, data, horário e serviço são obrigatórios."}), 400
    with get_db() as db:
        cur = db.execute("""INSERT INTO appointments(client_id,vehicle_id,date,time,service,status,notes)
                            VALUES(?,?,?,?,?,?,?)""",
                         (d["client_id"], d.get("vehicle_id") or None, d["date"], d["time"],
                          d["service"], d.get("status", "Agendado"), d.get("notes", "")))
        row = db.execute("SELECT * FROM appointments WHERE id=?", (cur.lastrowid,)).fetchone()
    return jsonify(dict(row)), 201


@app.patch("/api/appointments/<int:item_id>")
@login_required
def appointments_update(item_id):
    d = body()
    allowed = {"status": "status", "date": "date", "time": "time", "service": "service", "notes": "notes"}
    if not d or any(k not in allowed for k in d):
        return jsonify({"error": "Envie status, data, horário, serviço ou observações válidos."}), 400
    with get_db() as db:
        row = db.execute("SELECT * FROM appointments WHERE id=?", (item_id,)).fetchone()
        if not row:
            return jsonify({"error": "Agendamento não encontrado."}), 404
        values = {k: d.get(k, row[k]) for k in allowed}
        db.execute("UPDATE appointments SET status=?,date=?,time=?,service=?,notes=? WHERE id=?",
                   (values["status"], values["date"], values["time"], values["service"], values["notes"], item_id))
        updated = db.execute("SELECT * FROM appointments WHERE id=?", (item_id,)).fetchone()
    return jsonify(dict(updated))


@app.delete("/api/appointments/<int:item_id>")
@login_required
def appointments_delete(item_id):
    return delete_row("appointments", item_id)


@app.get("/api/orders")
@login_required
def orders_list():
    with get_db() as db:
        rows = db.execute("""SELECT w.*, c.name AS client_name, v.plate AS plate,
                             (w.labor+w.parts) AS total FROM work_orders w
                             JOIN clients c ON c.id=w.client_id LEFT JOIN vehicles v ON v.id=w.vehicle_id
                             ORDER BY w.id DESC""").fetchall()
    return jsonify([dict(r) for r in rows])


@app.post("/api/orders")
@login_required
def orders_create():
    d = body()
    if not d.get("client_id") or not str(d.get("description", "")).strip():
        return jsonify({"error": "Cliente e descrição do serviço são obrigatórios."}), 400
    with get_db() as db:
        cur = db.execute("""INSERT INTO work_orders(client_id,vehicle_id,description,status,labor,parts)
                            VALUES(?,?,?,?,?,?)""",
                         (d["client_id"], d.get("vehicle_id") or None, d["description"],
                          d.get("status", "Aberta"), float(d.get("labor") or 0), float(d.get("parts") or 0)))
        row = db.execute("SELECT * FROM work_orders WHERE id=?", (cur.lastrowid,)).fetchone()
    return jsonify(dict(row)), 201


@app.patch("/api/orders/<int:item_id>")
@login_required
def orders_update(item_id):
    d = body()
    status = d.get("status")
    if status not in ("Aberta", "Em andamento", "Aguardando peças", "Concluída", "Cancelada"):
        return jsonify({"error": "Status inválido."}), 400
    with get_db() as db:
        cur = db.execute("UPDATE work_orders SET status=? WHERE id=?", (status, item_id))
        if cur.rowcount == 0:
            return jsonify({"error": "Ordem de serviço não encontrada."}), 404
        row = db.execute("SELECT * FROM work_orders WHERE id=?", (item_id,)).fetchone()
    return jsonify(dict(row))


@app.delete("/api/orders/<int:item_id>")
@login_required
def orders_delete(item_id):
    return delete_row("work_orders", item_id)


@app.get("/api/transactions")
@login_required
def transactions_list():
    with get_db() as db:
        rows = db.execute("SELECT * FROM transactions ORDER BY date DESC, id DESC").fetchall()
    return jsonify([dict(r) for r in rows])


@app.post("/api/transactions")
@login_required
def transactions_create():
    d = body()
    if d.get("kind") not in ("Receita", "Despesa") or not str(d.get("description", "")).strip() or not d.get("date"):
        return jsonify({"error": "Tipo, descrição e data são obrigatórios."}), 400
    try:
        amount = float(d.get("amount", 0))
        if amount <= 0:
            raise ValueError()
    except (ValueError, TypeError):
        return jsonify({"error": "O valor precisa ser maior que zero."}), 400
    with get_db() as db:
        cur = db.execute("INSERT INTO transactions(kind,description,amount,date,notes) VALUES(?,?,?,?,?)",
                         (d["kind"], d["description"], amount, d["date"], d.get("notes", "")))
        row = db.execute("SELECT * FROM transactions WHERE id=?", (cur.lastrowid,)).fetchone()
    return jsonify(dict(row)), 201


@app.delete("/api/transactions/<int:item_id>")
@login_required
def transactions_delete(item_id):
    return delete_row("transactions", item_id)


init_db()

if __name__ == "__main__":
    app.run(debug=True)
