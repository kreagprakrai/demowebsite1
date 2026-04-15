from flask import Flask, render_template, request, redirect
import sqlite3

app = Flask(__name__, template_folder="templates")

def get_db():
    conn = sqlite3.connect("cakeshop.db")
    conn.row_factory = sqlite3.Row
    return conn

# สร้าง table ครั้งแรก
def init_db():
    conn = get_db()

    # Create categories table
    conn.execute("""
    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL
    )
    """)

    # Create cakes table with foreign key to categories
    conn.execute("""
    CREATE TABLE IF NOT EXISTS cakes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        price REAL,
        image TEXT,
        stock INTEGER DEFAULT 0,
        category_id INTEGER,
        FOREIGN KEY (category_id) REFERENCES categories (id)
    )
    """)

    # Add stock column to existing table if missing (safe on upgrade)
    try:
        conn.execute("ALTER TABLE cakes ADD COLUMN stock INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    # Add category_id column to existing table if missing (safe on upgrade)
    try:
        conn.execute("ALTER TABLE cakes ADD COLUMN category_id INTEGER REFERENCES categories(id)")
    except sqlite3.OperationalError:
        pass

    # Insert default categories if they don't exist
    default_categories = ["Chocolate", "Fruit", "Birthday", "Wedding", "Custom"]
    for cat in default_categories:
        try:
            conn.execute("INSERT INTO categories (name) VALUES (?)", (cat,))
        except sqlite3.IntegrityError:
            pass  # Category already exists

    conn.commit()
    conn.close()

init_db()

# หน้าเมนู
@app.route("/")
def cakemenu():
    conn = get_db()
    cakes = conn.execute("""
        SELECT cakes.*, categories.name as category_name
        FROM cakes
        LEFT JOIN categories ON cakes.category_id = categories.id
    """).fetchall()
    conn.close()
    return render_template("cakemenu.html", cakes=cakes)

# เพิ่มเมนู
@app.route("/append", methods=["GET", "POST"])
def append():
    conn = get_db()
    categories = conn.execute("SELECT * FROM categories").fetchall()

    if request.method == "POST":
        name = request.form["name"]
        price = request.form["price"]
        image = request.form["image"]
        stock = request.form.get("stock", "0")
        category_id = request.form.get("category_id")

        try:
            stock = int(stock)
        except ValueError:
            stock = 0

        try:
            category_id = int(category_id) if category_id else None
        except ValueError:
            category_id = None

        conn.execute("INSERT INTO cakes (name, price, image, stock, category_id) VALUES (?, ?, ?, ?, ?)",
                     (name, price, image, stock, category_id))
        conn.commit()
        conn.close()
        return redirect("/")

    conn.close()
    return render_template("append.html", categories=categories)

# แก้ไขเมนู
@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit(id):
    conn = get_db()
    categories = conn.execute("SELECT * FROM categories").fetchall()

    if request.method == "POST":
        name = request.form["name"]
        price = request.form["price"]
        image = request.form["image"]
        stock = request.form.get("stock", "0")
        category_id = request.form.get("category_id")

        try:
            stock = int(stock)
        except ValueError:
            stock = 0

        try:
            category_id = int(category_id) if category_id else None
        except ValueError:
            category_id = None

        conn.execute("UPDATE cakes SET name=?, price=?, image=?, stock=?, category_id=? WHERE id=?",
                     (name, price, image, stock, category_id, id))
        conn.commit()
        conn.close()
        return redirect("/")

    cake = conn.execute("""
        SELECT cakes.*, categories.name as category_name
        FROM cakes
        LEFT JOIN categories ON cakes.category_id = categories.id
        WHERE cakes.id=?
    """, (id,)).fetchone()
    conn.close()
    return render_template("edit.html", cake=cake, categories=categories)

# ลบ (แถมให้)
@app.route("/delete/<int:id>")
def delete(id):
    conn = get_db()
    conn.execute("DELETE FROM cakes WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True)
