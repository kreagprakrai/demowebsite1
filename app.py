from flask import Flask, render_template, request, redirect, url_for, flash
from database import get_db, init_db

app = Flask(__name__)
app.secret_key = "stock-secret-key"


@app.route("/")
def index():
    conn = get_db()

    products = conn.execute("""
        SELECT
            p.id,
            p.name,
            p.price,
            p.stock,
            p.category_id,
            c.name AS category_name
        FROM products p
        LEFT JOIN categories c ON p.category_id = c.id
        ORDER BY p.id DESC
    """).fetchall()

    summary = conn.execute("""
        SELECT
            COUNT(*) AS total_items,
            COALESCE(SUM(stock), 0) AS total_stock,
            COALESCE(SUM(price * stock), 0) AS total_value,
            COALESCE(SUM(CASE WHEN stock <= 5 THEN 1 ELSE 0 END), 0) AS low_stock_count
        FROM products
    """).fetchone()

    conn.close()
    return render_template("index.html", products=products, summary=summary)


@app.route("/add", methods=["GET", "POST"])
def add_item():
    conn = get_db()
    categories = conn.execute(
        "SELECT * FROM categories ORDER BY name"
    ).fetchall()

    if request.method == "POST":
        name = request.form["name"].strip()
        price = request.form.get("price", "0").strip()
        stock = request.form.get("stock", "0").strip()
        category_id = request.form.get("category_id") or None

        if not name:
            flash("กรุณากรอกชื่อสินค้า")
            conn.close()
            return redirect(url_for("add_item"))

        try:
            price = float(price)
            stock = int(stock)
            category_id = int(category_id) if category_id else None
        except ValueError:
            flash("ข้อมูลราคา / stock / หมวดหมู่ ไม่ถูกต้อง")
            conn.close()
            return redirect(url_for("add_item"))

        conn.execute("""
            INSERT INTO products (name, category_id, price, stock)
            VALUES (?, ?, ?, ?)
        """, (name, category_id, price, stock))

        conn.commit()
        conn.close()

        flash("เพิ่มสินค้าเรียบร้อยแล้ว")
        return redirect(url_for("index"))

    conn.close()
    return render_template("add.html", categories=categories)


@app.route("/edit/<int:item_id>", methods=["GET", "POST"])
def edit_item(item_id):
    conn = get_db()

    product = conn.execute("""
        SELECT * FROM products WHERE id = ?
    """, (item_id,)).fetchone()

    categories = conn.execute(
        "SELECT * FROM categories ORDER BY name"
    ).fetchall()

    if product is None:
        conn.close()
        flash("ไม่พบสินค้า")
        return redirect(url_for("index"))

    if request.method == "POST":
        name = request.form["name"].strip()
        price = request.form.get("price", "0").strip()
        stock = request.form.get("stock", "0").strip()
        category_id = request.form.get("category_id") or None

        if not name:
            flash("กรุณากรอกชื่อสินค้า")
            conn.close()
            return redirect(url_for("edit_item", item_id=item_id))

        try:
            price = float(price)
            stock = int(stock)
            category_id = int(category_id) if category_id else None
        except ValueError:
            flash("ข้อมูลราคา / stock / หมวดหมู่ ไม่ถูกต้อง")
            conn.close()
            return redirect(url_for("edit_item", item_id=item_id))

        conn.execute("""
            UPDATE products
            SET name = ?, price = ?, stock = ?, category_id = ?
            WHERE id = ?
        """, (name, price, stock, category_id, item_id))

        conn.commit()
        conn.close()

        flash("แก้ไขสินค้าเรียบร้อยแล้ว")
        return redirect(url_for("index"))

    conn.close()
    return render_template("edit.html", product=product, categories=categories)


@app.route("/delete/<int:item_id>")
def delete_item(item_id):
    conn = get_db()

    product = conn.execute("""
        SELECT * FROM products WHERE id = ?
    """, (item_id,)).fetchone()

    if product is None:
        conn.close()
        flash("ไม่พบสินค้า")
        return redirect(url_for("index"))

    conn.execute("DELETE FROM products WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()

    flash("ลบสินค้าเรียบร้อยแล้ว")
    return redirect(url_for("index"))


@app.route("/stock/update/<int:item_id>", methods=["POST"])
def update_stock(item_id):
    change = request.form.get("change", "0").strip()

    try:
        change = int(change)
    except ValueError:
        flash("จำนวน stock ไม่ถูกต้อง")
        return redirect(url_for("index"))

    conn = get_db()

    product = conn.execute("""
        SELECT * FROM products WHERE id = ?
    """, (item_id,)).fetchone()

    if product is None:
        conn.close()
        flash("ไม่พบสินค้า")
        return redirect(url_for("index"))

    new_stock = product["stock"] + change
    if new_stock < 0:
        new_stock = 0

    conn.execute("""
        UPDATE products
        SET stock = ?
        WHERE id = ?
    """, (new_stock, item_id))

    conn.execute("""
        INSERT INTO stock_logs (product_id, change_qty, note)
        VALUES (?, ?, ?)
    """, (item_id, change, "manual update"))

    conn.commit()
    conn.close()

    flash("อัปเดต stock เรียบร้อยแล้ว")
    return redirect(url_for("index"))



@app.route("/categories", methods=["GET", "POST"])
def manage_categories():
    conn = get_db()

    if request.method == "POST":
        name = request.form["name"].strip()

        if not name:
            flash("กรุณากรอกชื่อหมวดหมู่")
            conn.close()
            return redirect(url_for("manage_categories"))

        try:
            conn.execute("""
                INSERT INTO categories (name)
                VALUES (?)
            """, (name,))
            conn.commit()
            flash("เพิ่มหมวดหมู่เรียบร้อยแล้ว")
        except Exception:
            flash("หมวดหมู่นี้มีอยู่แล้วหรือบันทึกไม่ได้")

        conn.close()
        return redirect(url_for("manage_categories"))

    categories = conn.execute("""
        SELECT * FROM categories ORDER BY name
    """).fetchall()

    conn.close()
    return render_template("categories.html", categories=categories)

@app.route("/categories2", methods=["GET", "POST"])
def manage_categories2():
    conn = get_db()

    if request.method == "POST":
        name = request.form["name"].strip()

        if not name:
            flash("กรุณากรอกชื่อหมวดหมู่")
            conn.close()
            return redirect(url_for("manage_categories2"))

        try:
            conn.execute(
                "INSERT INTO categories2 (name) VALUES (?)",
                (name,)
            )
            conn.commit()
            flash("เพิ่มหมวดหมู่เรียบร้อยแล้ว")
        except Exception:
            flash("หมวดหมู่นี้มีอยู่แล้ว")

        conn.close()
        return redirect(url_for("manage_categories2"))

    categories2 = conn.execute(
        "SELECT * FROM categories2 ORDER BY name"
    ).fetchall()

    conn.close()
    return render_template("categories2.html", categories=categories2)

@app.route("/categories_add", methods=["GET", "POST"])
def manage_categories_add():
    conn = get_db()

    if request.method == "POST":
        name = request.form["name"].strip()

        if not name:
            flash("กรุณากรอกชื่อหมวดหมู่")
            conn.close()
            return redirect(url_for("manage_categories_add"))

        try:
            conn.execute(
                "INSERT INTO categories (name) VALUES (?)",
                (name,)
            )
            conn.commit()
            flash("เพิ่มหมวดหมู่เรียบร้อยแล้ว")
        except Exception:
            flash("หมวดหมู่นี้มีอยู่แล้ว")

        conn.close()
        return redirect(url_for("manage_categories_add"))

    categories = conn.execute(
        "SELECT * FROM categories ORDER BY name"
    ).fetchall()

    conn.close()
    return render_template("categories.html", categories=categories)

if __name__ == "__main__":
    init_db()
    app.run(debug=True)