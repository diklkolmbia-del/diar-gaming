import os
import sqlite3
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, abort
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-before-publishing")
DB_PATH = os.environ.get("DATABASE_PATH", "diar_gaming.db")

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with db() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            summary TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        con.execute("""CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )""")
        if not con.execute("SELECT id FROM admins LIMIT 1").fetchone():
            username = os.environ.get("ADMIN_USERNAME", "admin")
            password = os.environ.get("ADMIN_PASSWORD", "ChangeMe123!")
            con.execute("INSERT INTO admins (username, password_hash) VALUES (?, ?)",
                        (username, generate_password_hash(password)))
        if not con.execute("SELECT id FROM posts LIMIT 1").fetchone():
            samples = [
                ("۵ نکته برای بهتر شدن در بازی‌های رقابتی", "آموزش", "چند عادت ساده برای تمرین بهتر و بازی هوشمندانه‌تر.", "برای پیشرفت در بازی‌های رقابتی، تنظیمات مناسب را انتخاب کنید، نقشه را بشناسید، با هم‌تیمی‌ها ارتباط محترمانه داشته باشید و بعد از هر مسابقه عملکرد خود را مرور کنید."),
                ("بازی‌های مستقل؛ تجربه‌هایی متفاوت", "معرفی بازی", "چرا بازی‌های مستقل ارزش امتحان کردن دارند؟", "بازی‌های مستقل معمولاً ایده‌های تازه و سبک‌های هنری متفاوتی ارائه می‌کنند. هنگام انتخاب بازی، رده‌بندی سنی و مشخصات دستگاه خود را بررسی کنید."),
                ("خبرهای دنیای بازی را از کجا دنبال کنیم؟", "اخبار", "چند روش برای تشخیص خبر معتبر از شایعه.", "برای بررسی خبرها، اطلاعیه‌های رسمی سازندگان و رسانه‌های شناخته‌شده را در اولویت قرار دهید. تاریخ انتشار و منبع خبر را هم بررسی کنید.")
            ]
            con.executemany("INSERT INTO posts (title, category, summary, content) VALUES (?, ?, ?, ?)", samples)

def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("admin_id"):
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper

@app.route("/")
def home():
    with db() as con:
        posts = con.execute("SELECT * FROM posts ORDER BY created_at DESC, id DESC").fetchall()
    return render_template("index.html", posts=posts)

@app.route("/article/<int:post_id>")
def article(post_id):
    with db() as con:
        post = con.execute("SELECT * FROM posts WHERE id = ?", (post_id,)).fetchone()
    if not post:
        abort(404)
    return render_template("article.html", post=post)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        with db() as con:
            admin = con.execute("SELECT * FROM admins WHERE username = ?", (username,)).fetchone()
        if admin and check_password_hash(admin["password_hash"], password):
            session.clear()
            session["admin_id"] = admin["id"]
            session["admin_name"] = admin["username"]
            return redirect(url_for("dashboard"))
        flash("نام کاربری یا رمز عبور اشتباه است.")
    return render_template("login.html")

@app.route("/admin")
@admin_required
def dashboard():
    with db() as con:
        posts = con.execute("SELECT * FROM posts ORDER BY id DESC").fetchall()
    return render_template("dashboard.html", posts=posts)

@app.route("/admin/new", methods=["GET", "POST"])
@admin_required
def new_post():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        category = request.form.get("category", "").strip()
        summary = request.form.get("summary", "").strip()
        content = request.form.get("content", "").strip()
        if not all([title, category, summary, content]):
            flash("لطفاً همه قسمت‌ها را کامل کن.")
        else:
            with db() as con:
                con.execute("INSERT INTO posts (title, category, summary, content) VALUES (?, ?, ?, ?)",
                            (title, category, summary, content))
            flash("مطلب با موفقیت منتشر شد.")
            return redirect(url_for("dashboard"))
    return render_template("new_post.html")

@app.post("/admin/delete/<int:post_id>")
@admin_required
def delete_post(post_id):
    with db() as con:
        con.execute("DELETE FROM posts WHERE id = ?", (post_id,))
    flash("مطلب حذف شد.")
    return redirect(url_for("dashboard"))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

@app.errorhandler(404)
def not_found(_):
    return render_template("404.html"), 404

init_db()

if __name__ == "__main__":
    app.run(debug=True)
