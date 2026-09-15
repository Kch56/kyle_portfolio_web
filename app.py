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


CURRENT_PROJECTS = {
    "charlotte-neighborhood-change": {
        "title": "Mapping Charlotte's Changing Neighborhoods",
        "status": "Completed",
        "summary": "An exploratory data science study of housing affordability pressure and displacement vulnerability across Mecklenburg County census tracts and Charlotte neighborhoods.",
        "overview": "This project began with a broad question about displacement risk and gentrification. After reviewing the available data, I narrowed the analysis to outcomes the datasets could support: characteristics associated with rent burden across Mecklenburg County census tracts and a separate description of the City of Charlotte's displacement-vulnerability classification. Keeping those analyses separate prevented the project from treating a constructed vulnerability score as proof that displacement occurred.",
        "original_question": "What housing, demographic, and economic factors are most strongly associated with displacement risk in Charlotte neighborhoods, and to what extent can changes in affordable housing, income, and housing costs identify communities experiencing gentrification?",
        "question": "Which housing, demographic, and economic characteristics are associated with rent burden across Mecklenburg County census tracts, and how do separate city data describe neighborhood displacement vulnerability?",
        "contribution": "I collected public data through the U.S. Census Bureau and City of Charlotte APIs, cleaned and merged tract-level measurements, handled missing observations, explored housing and demographic variables, and created visualizations to compare affordability patterns. I also documented the limits of the analysis so associations would not be presented as causal findings.",
        "impact": "The question remains relevant to residents, housing organizations, and local planners because affordability pressure may leave households less able to absorb a rent increase or income loss. The analysis identifies patterns worth investigating, but it does not estimate a household's probability of displacement or identify neighborhoods that have gentrified.",
        "tools": ["Python", "Pandas", "Census API", "ArcGIS REST API", "Data Visualization", "Statistical Analysis"],
        "sources": [
            {
                "name": "U.S. Census Bureau, 2024 ACS Five-Year API",
                "url": "https://api.census.gov/data/2024/acs/acs5.html",
                "role": "Provided 2020–2024 estimates of income, rent, population, rent burden, employment, education, racial and ethnic composition, and housing tenure.",
            },
            {
                "name": "City of Charlotte, Vulnerability to Displacement by NPA",
                "url": "https://gis.charlottenc.gov/arcgis/rest/services/ODP/City_Space_ODP_Data/MapServer/1",
                "role": "Provided the City vulnerability score and classification, along with poverty, homeownership, education, age, and demographic fields.",
            },
            {
                "name": "City of Charlotte, Housing Locational Tool",
                "url": "https://gis.charlottenc.gov/arcgis/rest/services/HNS/NPA_HLT/FeatureServer/0",
                "role": "Provided July 2025 neighborhood income for a separate NPA comparison. Sales-price fields were investigated but not used for conclusions.",
            },
        ],
    },
    "emergency-response-modeling": {
        "title": "Emergency Response Modeling",
        "status": "Ongoing",
        "summary": "Spatial analysis tools for studying response coverage, travel patterns, and planning scenarios.",
        "overview": "This work uses historical and geographic information to study how emergency resources move through a growing city. It replaces broad assumptions with patterns grounded in actual operating conditions while keeping the results understandable for nontechnical users.",
        "question": "How can historical travel information and spatial modeling support more realistic response-planning scenarios?",
        "contribution": "I prepare and validate location-based data, build analysis workflows in Python, compare travel patterns across time and geography, and turn the results into maps and planning outputs.",
        "impact": "The project gives planners another evidence-based way to explore coverage, compare scenarios, and discuss where further investigation may be useful.",
        "tools": ["Python", "GIS", "GeoPandas", "Spatial Analysis", "Data Preparation"],
    },
    "risk-informed-planning": {
        "title": "Risk-Informed Planning",
        "status": "Ongoing",
        "summary": "Clear and explainable ways to combine location-based information with operational planning.",
        "overview": "This project explores how several indicators can be organized into a consistent planning framework. The focus is on making every classification traceable so users can understand why an area receives a result instead of seeing a score with no explanation.",
        "question": "How can location-based indicators support planning while preserving transparency and human review?",
        "contribution": "I research possible indicators, prepare spatial datasets, document assumptions, compare classification approaches, and design outputs that allow users to review the information behind each result.",
        "impact": "The work supports more consistent scenario analysis while keeping professional judgment and review at the center of the process.",
        "tools": ["GIS", "Data Architecture", "Research", "Process Design", "Data Visualization"],
    },
    "grant-research-tool": {
        "title": "Grant Research Tool",
        "status": "In Development",
        "summary": "A tool that helps teams search, organize, and review funding opportunities more efficiently.",
        "overview": "Grant research often means reviewing information spread across many websites and documents. This application concept brings the most useful details into one place so users can spend less time sorting through unrelated opportunities.",
        "question": "How can a lightweight application make grant discovery and review faster without removing human decision-making?",
        "contribution": "I am designing the search workflow, organizing grant fields, building the Flask interface, and testing ways to filter results by eligibility, topic, deadline, and organizational need.",
        "impact": "The tool is intended to reduce repetitive searching and give teams a clearer starting point for deciding which opportunities deserve a closer review.",
        "tools": ["Flask", "Python", "Search", "Data Organization", "UI/UX"],
    },
    "mapbook-automation": {
        "title": "Mapbook Automation",
        "status": "Ongoing",
        "summary": "Repeatable workflows for producing consistent maps and planning materials as data changes.",
        "overview": "Mapbooks can become time-consuming when each update requires the same manual preparation. This project turns recurring map-production steps into a repeatable workflow while keeping layouts and labels consistent.",
        "question": "How can map production be automated without losing the quality checks needed for useful planning documents?",
        "contribution": "I organize geographic data, build automated processing steps, create consistent layouts, and review the generated maps for missing features, labeling issues, and other quality problems.",
        "impact": "The workflow reduces repetitive work and makes it easier to produce updated planning materials when source data changes.",
        "tools": ["Python", "GIS", "Automation", "Mapping", "Documentation"],
    },
    "internal-request-routing": {
        "title": "Internal Request Routing",
        "status": "In Development",
        "summary": "A simpler way for staff to find the correct process, resource, or team for common requests.",
        "overview": "Internal services can be hard to navigate when guidance is scattered across documents and systems. This project organizes common request types into a clearer path from the user's question to the right next step.",
        "question": "How can an internal tool reduce confusion and route users to the right resource more consistently?",
        "contribution": "I map existing workflows, identify common decision points, organize guidance, and design an interface that asks users only for the information needed to direct their request.",
        "impact": "The concept can reduce misrouted requests, save staff time, and make internal processes easier to understand.",
        "tools": ["Workflow Design", "Application Development", "Process Mapping", "UI/UX"],
    },
    "department-mobile-app": {
        "title": "Department Mobile App Concept",
        "status": "Planning",
        "summary": "A mobile-friendly resource hub for guidance, references, and common workflows.",
        "overview": "This concept explores how frequently used information could be organized for quick access from a phone. The emphasis is on simple navigation, readable content, and features that solve common day-to-day needs.",
        "question": "What information and workflows would be most useful in a secure, mobile-friendly internal resource hub?",
        "contribution": "I am gathering requirements, organizing possible features, sketching user flows, and evaluating how the experience should change across phone and desktop screens.",
        "impact": "The project provides a practical starting point for discussing user needs, technical requirements, and the value of a department-focused mobile experience.",
        "tools": ["Product Design", "Mobile UX", "Requirements Gathering", "Internal Tools"],
    },
    "snowflake-data-integration": {
        "title": "Snowflake Data Integration & Analytics",
        "status": "Ongoing",
        "summary": "Reliable data workflows that support reporting, analysis, and system integration.",
        "overview": "This work connects cloud data with downstream reporting and business processes. The focus is not only moving records between systems, but also preserving data types, handling missing values, validating results, and documenting how each field should be used.",
        "question": "How can data move between systems accurately and repeatedly while remaining useful to both technical and operational teams?",
        "contribution": "I write SQL and Python workflows, map fields between source and destination structures, apply validation rules, investigate errors, and compare outputs against business requirements.",
        "impact": "These workflows reduce manual preparation, improve consistency, and give teams more confidence that the information used in reports and other processes matches the source.",
        "tools": ["Snowflake", "SQL", "Python", "Pandas", "Data Validation", "Data Integration"],
    },
}


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


@app.route("/current-projects/<slug>")
def current_project_detail(slug):
    project = CURRENT_PROJECTS.get(slug)
    if project is None:
        abort(404)
    return render_template("current_project_detail.html", project=project)


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
