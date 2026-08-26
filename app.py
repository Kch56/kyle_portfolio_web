import os
import secrets
import sqlite3
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path

from flask import Flask, abort, flash, redirect, render_template, request, session, url_for
from flask_mail import Mail, Message
from werkzeug.security import check_password_hash


BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = Path(os.getenv("BLOG_DB_PATH", BASE_DIR / "data" / "blog.db"))

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.getenv("SECRET_KEY", secrets.token_hex(32)),
    MAIL_SERVER=os.getenv("MAIL_SERVER", "smtp.gmail.com"),
    MAIL_PORT=int(os.getenv("MAIL_PORT", "465")),
    MAIL_USE_TLS=os.getenv("MAIL_USE_TLS", "false").lower() == "true",
    MAIL_USE_SSL=os.getenv("MAIL_USE_SSL", "true").lower() == "true",
    MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),
    MAIL_DEFAULT_SENDER=os.getenv("MAIL_DEFAULT_SENDER", os.getenv("MAIL_USERNAME")),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.getenv("FLASK_ENV") == "production",
)
mail = Mail(app)


def get_db():
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    with get_db() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                slug TEXT NOT NULL UNIQUE,
                excerpt TEXT NOT NULL,
                body TEXT NOT NULL,
                published INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )


def csrf_token():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(32)
    return session["csrf_token"]


app.jinja_env.globals["csrf_token"] = csrf_token


def validate_csrf():
    submitted = request.form.get("csrf_token", "")
    expected = session.get("csrf_token", "")
    if not expected or not secrets.compare_digest(submitted, expected):
        abort(400)


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("blog_admin"):
            return redirect(url_for("admin_login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


def valid_admin_password(password):
    password_hash = os.getenv("BLOG_PASSWORD_HASH")
    plain_password = os.getenv("BLOG_ADMIN_PASSWORD")
    if password_hash:
        return check_password_hash(password_hash, password)
    if plain_password:
        return secrets.compare_digest(password, plain_password)
    return False


def slugify(value):
    safe = "".join(character.lower() if character.isalnum() else "-" for character in value)
    return "-".join(part for part in safe.split("-") if part)[:80]


@app.before_request
def ensure_database():
    init_db()


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/projects")
def projects():
    return render_template("projects.html")


@app.route("/current-projects")
def current_projects():
    return render_template("current_projects.html")


@app.route("/research")
def research():
    return render_template("research.html")


@app.route("/articles")
@app.route("/press")
def articles():
    return render_template("articles.html")


@app.route("/resume")
def resume():
    return render_template("resume.html")


@app.route("/blog")
def blog():
    with get_db() as connection:
        posts = connection.execute(
            "SELECT * FROM posts WHERE published = 1 ORDER BY created_at DESC"
        ).fetchall()
    return render_template("blog.html", posts=posts)


@app.route("/blog/<slug>")
def blog_post(slug):
    with get_db() as connection:
        post = connection.execute(
            "SELECT * FROM posts WHERE slug = ? AND published = 1", (slug,)
        ).fetchone()
    if post is None:
        abort(404)
    return render_template("blog_post.html", post=post)


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        validate_csrf()
        if valid_admin_password(request.form.get("password", "")):
            session.clear()
            session["blog_admin"] = True
            session["csrf_token"] = secrets.token_urlsafe(32)
            return redirect(url_for("admin_posts"))
        flash("That password was not accepted.", "error")
    return render_template("admin_login.html")


@app.route("/admin/logout", methods=["POST"])
@admin_required
def admin_logout():
    validate_csrf()
    session.clear()
    return redirect(url_for("blog"))


@app.route("/admin/posts")
@admin_required
def admin_posts():
    with get_db() as connection:
        posts = connection.execute("SELECT * FROM posts ORDER BY created_at DESC").fetchall()
    return render_template("admin_posts.html", posts=posts)


@app.route("/admin/posts/new", methods=["GET", "POST"])
@admin_required
def admin_post_new():
    if request.method == "POST":
        validate_csrf()
        now = datetime.now(timezone.utc).isoformat()
        title = request.form["title"].strip()
        slug = slugify(request.form.get("slug") or title)
        with get_db() as connection:
            connection.execute(
                "INSERT INTO posts (title, slug, excerpt, body, published, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (title, slug, request.form["excerpt"].strip(), request.form["body"].strip(), 1 if request.form.get("published") else 0, now, now),
            )
        flash("Post created.", "success")
        return redirect(url_for("admin_posts"))
    return render_template("admin_post_form.html", post=None)


@app.route("/admin/posts/<int:post_id>/edit", methods=["GET", "POST"])
@admin_required
def admin_post_edit(post_id):
    with get_db() as connection:
        post = connection.execute("SELECT * FROM posts WHERE id = ?", (post_id,)).fetchone()
        if post is None:
            abort(404)
        if request.method == "POST":
            validate_csrf()
            title = request.form["title"].strip()
            connection.execute(
                "UPDATE posts SET title = ?, slug = ?, excerpt = ?, body = ?, published = ?, updated_at = ? WHERE id = ?",
                (title, slugify(request.form.get("slug") or title), request.form["excerpt"].strip(), request.form["body"].strip(), 1 if request.form.get("published") else 0, datetime.now(timezone.utc).isoformat(), post_id),
            )
            flash("Post updated.", "success")
            return redirect(url_for("admin_posts"))
    return render_template("admin_post_form.html", post=post)


@app.route("/admin/posts/<int:post_id>/delete", methods=["POST"])
@admin_required
def admin_post_delete(post_id):
    validate_csrf()
    with get_db() as connection:
        connection.execute("DELETE FROM posts WHERE id = ?", (post_id,))
    flash("Post deleted.", "success")
    return redirect(url_for("admin_posts"))


@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        validate_csrf()
        if not app.config.get("MAIL_USERNAME") or not app.config.get("MAIL_PASSWORD"):
            flash("Email delivery is being configured. Please use the email link instead.", "error")
            return redirect(url_for("contact"))
        message = Message(
            f"Portfolio message from {request.form['name']}",
            recipients=[os.getenv("CONTACT_RECIPIENT", "kylehampton949@gmail.com")],
        )
        message.body = f"From: {request.form['name']} ({request.form['email']})\n\n{request.form['message']}"
        mail.send(message)
        flash("Thanks. Your message was sent.", "success")
        return redirect(url_for("contact"))
    return render_template("contact.html")


@app.errorhandler(404)
def not_found(_error):
    return render_template("404.html"), 404


if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG") == "1")
