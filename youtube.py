from flask import Flask, render_template_string, request, redirect, url_for, session, flash, send_from_directory
import sqlite3
import os
from uuid import uuid4
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "change-this-secret-key"

DB_NAME = "website.db"
UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"mp4", "webm"}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

ADMIN_EMAIL = "admin@gmail.com"
ADMIN_PASSWORD = "admin123"


# ---------------- DATABASE ----------------
def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
    """)

    cur.execute("PRAGMA table_info(users)")
    user_columns = [row["name"] for row in cur.fetchall()]
    if "is_admin" not in user_columns:
        cur.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            filename TEXT,
            mimetype TEXT,
            url TEXT NOT NULL
        )
    """)

    cur.execute("PRAGMA table_info(videos)")
    video_columns = [row["name"] for row in cur.fetchall()]
    if "filename" not in video_columns:
        cur.execute("ALTER TABLE videos ADD COLUMN filename TEXT")
    if "mimetype" not in video_columns:
        cur.execute("ALTER TABLE videos ADD COLUMN mimetype TEXT")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id INTEGER NOT NULL,
            user_email TEXT NOT NULL,
            comment TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("SELECT id FROM users WHERE email = ?", (ADMIN_EMAIL,))
    admin = cur.fetchone()
    if admin is None:
        cur.execute("""
            INSERT INTO users (username, email, password, is_admin)
            VALUES (?, ?, ?, 1)
        """, ("Admin", ADMIN_EMAIL, generate_password_hash(ADMIN_PASSWORD)))

    conn.commit()
    conn.close()


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# ---------------- HTML PAGES ----------------
REGISTER_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Register</title>
    <style>
        body { margin: 0; font-family: Arial, sans-serif; background: linear-gradient(180deg, #111, #222); color: white; }
        .phone { max-width: 420px; margin: 0 auto; min-height: 100vh; padding: 20px; box-sizing: border-box; }
        .card { background: #fff; color: #111; border-radius: 20px; padding: 20px; margin-top: 40px; box-shadow: 0 10px 25px rgba(0,0,0,0.25); }
        input, button { width: 100%; padding: 14px; margin: 8px 0; border-radius: 12px; border: 1px solid #ccc; box-sizing: border-box; font-size: 16px; }
        button { background: #ff0000; color: white; border: none; font-weight: bold; }
        a { color: #ff3b3b; text-decoration: none; font-weight: bold; }
        .msg { padding: 12px; border-radius: 12px; margin-bottom: 12px; }
        .success { background: #e7ffe7; color: #0b6b0b; }
        .error { background: #ffe7e7; color: #9a1111; }
    </style>
</head>
<body>
    <div class="phone">
        <div class="card">
            <h1>Create Account</h1>

            {% with messages = get_flashed_messages(with_categories=true) %}
              {% if messages %}
                {% for category, message in messages %}
                  <div class="msg {{ category }}">{{ message }}</div>
                {% endfor %}
              {% endif %}
            {% endwith %}

            <form method="post" action="{{ url_for('register') }}">
                <input type="text" name="username" placeholder="Username" required>
                <input type="email" name="email" placeholder="Email" required>
                <input type="password" name="password" placeholder="Password" required>
                <button type="submit">Register</button>
            </form>

            <p>Already have account? <a href="{{ url_for('login') }}">Go to Login</a></p>
        </div>
    </div>
</body>
</html>
"""

LOGIN_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login</title>
    <style>
        body { margin: 0; font-family: Arial, sans-serif; background: linear-gradient(180deg, #111, #222); color: white; }
        .phone { max-width: 420px; margin: 0 auto; min-height: 100vh; padding: 20px; box-sizing: border-box; }
        .card { background: #fff; color: #111; border-radius: 20px; padding: 20px; margin-top: 40px; box-shadow: 0 10px 25px rgba(0,0,0,0.25); }
        input, button { width: 100%; padding: 14px; margin: 8px 0; border-radius: 12px; border: 1px solid #ccc; box-sizing: border-box; font-size: 16px; }
        button { background: #ff0000; color: white; border: none; font-weight: bold; }
        a { color: #ff3b3b; text-decoration: none; font-weight: bold; }
        .msg { padding: 12px; border-radius: 12px; margin-bottom: 12px; }
        .success { background: #e7ffe7; color: #0b6b0b; }
        .error { background: #ffe7e7; color: #9a1111; }
    </style>
</head>
<body>
    <div class="phone">
        <div class="card">
            <h1>Sign In</h1>

            {% with messages = get_flashed_messages(with_categories=true) %}
              {% if messages %}
                {% for category, message in messages %}
                  <div class="msg {{ category }}">{{ message }}</div>
                {% endfor %}
              {% endif %}
            {% endwith %}

            <form method="post" action="{{ url_for('login') }}">
                <input type="email" name="email" placeholder="Email" required>
                <input type="password" name="password" placeholder="Password" required>
                <button type="submit">Login</button>
            </form>

            <p>New user? <a href="{{ url_for('register') }}">Create account</a></p>
        </div>
    </div>
</body>
</html>
"""

DASHBOARD_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard</title>
    <style>
        body { margin: 0; font-family: Arial, sans-serif; background: #f2f2f2; }
        .topbar { background: #111; color: white; padding: 16px; position: sticky; top: 0; }
        .container { max-width: 800px; margin: auto; padding: 16px; }
        .card { background: white; border-radius: 18px; padding: 16px; margin-bottom: 16px; box-shadow: 0 6px 16px rgba(0,0,0,0.08); }
        .video-card h3 { margin-top: 0; }
        input, textarea, button { width: 100%; padding: 12px; margin: 8px 0; border-radius: 12px; border: 1px solid #ccc; box-sizing: border-box; font-size: 15px; }
        button { background: #ff0000; color: white; border: none; font-weight: bold; }
        .btn-secondary { background: #333; display: inline-block; text-align: center; text-decoration: none; color: white; padding: 12px; border-radius: 12px; }
        .btn-delete { background: #222; color: white; border: none; width: 100%; padding: 12px; border-radius: 12px; font-weight: bold; margin-top: 8px; }
        a { color: #0057cc; text-decoration: none; }
        .msg { padding: 12px; border-radius: 12px; margin-bottom: 12px; }
        .success { background: #e7ffe7; color: #0b6b0b; }
        .error { background: #ffe7e7; color: #9a1111; }
        .small { color: #666; font-size: 14px; }
        .video-link { display: inline-block; margin-right: 10px; margin-top: 6px; }
        .admin-badge { display:inline-block; background:#ff0000; color:white; padding:4px 10px; border-radius:999px; font-size:12px; margin-left:8px; }
    </style>
</head>
<body>
    <div class="topbar">
        <h2 style="margin:0;">Welcome, {{ username }}
            {% if is_admin %}
                <span class="admin-badge">ADMIN</span>
            {% endif %}
        </h2>
        <div class="small">{{ email }}</div>
        <p style="margin:8px 0 0 0;">Users can view videos. Only admin can upload/delete.</p>
    </div>

    <div class="container">
        {% with messages = get_flashed_messages(with_categories=true) %}
          {% if messages %}
            {% for category, message in messages %}
              <div class="msg {{ category }}">{{ message }}</div>
            {% endfor %}
          {% endif %}
        {% endwith %}

        <div class="card">
            <input type="text" id="searchBox" placeholder="Search videos..." onkeyup="filterVideos()">
            <a class="btn-secondary" href="{{ url_for('logout') }}">Logout</a>
        </div>

        {% if is_admin %}
        <div class="card">
            <h3>Upload Video</h3>
            <form method="post" action="{{ url_for('upload_video') }}" enctype="multipart/form-data">
                <input type="text" name="title" placeholder="Video title" required>
                <textarea name="description" rows="3" placeholder="Video description"></textarea>
                <input type="file" name="video_file" accept="video/mp4,video/webm" required>
                <button type="submit">Upload</button>
            </form>
        </div>
        {% endif %}

        <div id="videoList">
            {% for video in videos %}
            <div class="card video-card">
                <h3 class="video-title">{{ video['title'] }}</h3>
                <p class="video-desc">{{ video['description'] }}</p>
                <p><b>Video ID:</b> {{ video['id'] }}</p>

                {% if video['is_uploaded'] %}
                    <video width="100%" controls preload="metadata" playsinline>
                        <source src="{{ video['url'] }}" type="{{ video['mimetype'] or 'video/mp4' }}">
                        Your browser does not support video tag.
                    </video>
                {% endif %}

                <a class="video-link" href="{{ video['url'] }}" target="_blank">Watch Video</a>
                <a class="video-link" href="{{ url_for('comments_page', video_id=video['id']) }}">View Comments</a>

                <form method="post" action="{{ url_for('add_comment', video_id=video['id']) }}">
                    <textarea name="comment" rows="3" placeholder="Write a comment..." required></textarea>
                    <button type="submit">Post Comment</button>
                </form>

                {% if is_admin and video['is_uploaded'] %}
                <form method="post" action="{{ url_for('delete_video', video_id=video['id']) }}" onsubmit="return confirm('Delete this video?');">
                    <button type="submit" class="btn-delete">Delete Video</button>
                </form>
                {% endif %}
            </div>
            {% endfor %}
        </div>
    </div>

    <script>
        function filterVideos() {
            const query = document.getElementById("searchBox").value.toLowerCase();
            const cards = document.querySelectorAll(".video-card");

            cards.forEach(card => {
                const title = card.querySelector(".video-title").innerText.toLowerCase();
                const desc = card.querySelector(".video-desc").innerText.toLowerCase();
                card.style.display = (title.includes(query) || desc.includes(query)) ? "block" : "none";
            });
        }
    </script>
</body>
</html>
"""

COMMENTS_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Comments</title>
    <style>
        body { margin: 0; font-family: Arial, sans-serif; background: #f2f2f2; }
        .container { max-width: 700px; margin: auto; padding: 16px; }
        .card { background: white; border-radius: 18px; padding: 16px; margin-bottom: 16px; box-shadow: 0 6px 16px rgba(0,0,0,0.08); }
        input, textarea, button { width: 100%; padding: 12px; margin: 8px 0; border-radius: 12px; border: 1px solid #ccc; box-sizing: border-box; font-size: 15px; }
        button { background: #ff0000; color: white; border: none; font-weight: bold; }
        a { color: #0057cc; text-decoration: none; font-weight: bold; }
        .comment-item { border-top: 1px solid #eee; padding-top: 10px; margin-top: 10px; }
        .small { color: #666; font-size: 14px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="card">
            <h2>{{ video['title'] }}</h2>
            <p>{{ video['description'] }}</p>
            <a href="{{ url_for('dashboard') }}">← Back to Dashboard</a>
        </div>

        <div class="card">
            <h3>Add Comment</h3>
            <form method="post" action="{{ url_for('add_comment', video_id=video['id']) }}">
                <textarea name="comment" rows="4" placeholder="Write a comment..." required></textarea>
                <button type="submit">Post Comment</button>
            </form>
        </div>

        <div class="card">
            <h3>All Comments</h3>
            {% if comments %}
                {% for c in comments %}
                    <div class="comment-item">
                        <b>{{ c['user_email'] }}</b>
                        <p>{{ c['comment'] }}</p>
                        <div class="small">{{ c['created_at'] }}</div>
                    </div>
                {% endfor %}
            {% else %}
                <p>No comments yet.</p>
            {% endif %}
        </div>
    </div>
</body>
</html>
"""


# ---------------- ROUTES ----------------
@app.route("/")
def index():
    if "user_email" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("register"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if "user_email" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()

        if not username or not email or not password:
            flash("All fields are required", "error")
            return render_template_string(REGISTER_PAGE)

        if email.lower() == ADMIN_EMAIL.lower():
            flash("This email is reserved for admin", "error")
            return render_template_string(REGISTER_PAGE)

        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO users (username, email, password, is_admin) VALUES (?, ?, ?, 0)",
                (username, email, generate_password_hash(password))
            )
            conn.commit()
            conn.close()
            flash("Registered successfully. Now login.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Email already exists", "error")
            return render_template_string(REGISTER_PAGE)

    return render_template_string(REGISTER_PAGE)


@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_email" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()

        if not email or not password:
            flash("Email and password are required", "error")
            return render_template_string(LOGIN_PAGE)

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = cur.fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):
            session["user_email"] = user["email"]
            session["username"] = user["username"]
            session["is_admin"] = bool(user["is_admin"])
            flash("Login successful", "success")
            return redirect(url_for("dashboard"))

        flash("Invalid email or password", "error")
        return render_template_string(LOGIN_PAGE)

    return render_template_string(LOGIN_PAGE)


@app.route("/dashboard")
def dashboard():
    if "user_email" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM videos ORDER BY id DESC")
    raw_videos = cur.fetchall()
    conn.close()

    videos = []
    for v in raw_videos:
        is_uploaded = bool(v["filename"])
        videos.append({
            "id": v["id"],
            "title": v["title"],
            "description": v["description"] or "",
            "url": v["url"],
            "filename": v["filename"] or "",
            "mimetype": v["mimetype"] or "video/mp4",
            "is_uploaded": is_uploaded
        })

    return render_template_string(
        DASHBOARD_PAGE,
        username=session.get("username"),
        email=session.get("user_email"),
        is_admin=session.get("is_admin", False),
        videos=videos
    )


@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully", "success")
    return redirect(url_for("login"))


@app.route("/upload", methods=["POST"])
def upload_video():
    if "user_email" not in session:
        return redirect(url_for("login"))

    if not session.get("is_admin", False):
        flash("Only admin can upload videos", "error")
        return redirect(url_for("dashboard"))

    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    file = request.files.get("video_file")

    if not title or not file or file.filename == "":
        flash("Title and video file are required", "error")
        return redirect(url_for("dashboard"))

    if not allowed_file(file.filename):
        flash("Only mp4 and webm files are allowed", "error")
        return redirect(url_for("dashboard"))

    safe_name = secure_filename(file.filename)
    unique_name = f"{uuid4().hex}_{safe_name}"
    file_path = os.path.join(app.config["UPLOAD_FOLDER"], unique_name)
    file.save(file_path)

    video_url = url_for("uploaded_file", filename=unique_name)
    mime_type = file.mimetype or "video/mp4"

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO videos (title, description, filename, mimetype, url) VALUES (?, ?, ?, ?, ?)",
        (title, description, unique_name, mime_type, video_url)
    )
    conn.commit()
    conn.close()

    flash("Video uploaded successfully", "success")
    return redirect(url_for("dashboard"))


@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


@app.route("/delete/<int:video_id>", methods=["POST"])
def delete_video(video_id):
    if "user_email" not in session:
        return redirect(url_for("login"))

    if not session.get("is_admin", False):
        flash("Only admin can delete videos", "error")
        return redirect(url_for("dashboard"))

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM videos WHERE id = ?", (video_id,))
    video = cur.fetchone()

    if video is None:
        conn.close()
        flash("Video not found", "error")
        return redirect(url_for("dashboard"))

    if video["filename"]:
        file_path = os.path.join(app.config["UPLOAD_FOLDER"], video["filename"])
        if os.path.exists(file_path):
            os.remove(file_path)

    cur.execute("DELETE FROM comments WHERE video_id = ?", (video_id,))
    cur.execute("DELETE FROM videos WHERE id = ?", (video_id,))
    conn.commit()
    conn.close()

    flash("Video deleted successfully", "success")
    return redirect(url_for("dashboard"))


@app.route("/comment/<int:video_id>", methods=["POST"])
def add_comment(video_id):
    if "user_email" not in session:
        return redirect(url_for("login"))

    comment = request.form.get("comment", "").strip()
    if not comment:
        flash("Comment cannot be empty", "error")
        return redirect(url_for("dashboard"))

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO comments (video_id, user_email, comment) VALUES (?, ?, ?)",
        (video_id, session["user_email"], comment)
    )
    conn.commit()
    conn.close()

    flash("Comment added successfully", "success")
    return redirect(url_for("comments_page", video_id=video_id))


@app.route("/comments/<int:video_id>")
def comments_page(video_id):
    if "user_email" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM videos WHERE id = ?", (video_id,))
    video = cur.fetchone()

    cur.execute("""
        SELECT * FROM comments
        WHERE video_id = ?
        ORDER BY created_at DESC
    """, (video_id,))
    comments = cur.fetchall()
    conn.close()

    if video is None:
        flash("Video not found", "error")
        return redirect(url_for("dashboard"))

    return render_template_string(COMMENTS_PAGE, video=video, comments=comments)


if __name__ == "__main__":
    init_db()
    app.run(debug=True)