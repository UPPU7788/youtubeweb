from flask import Flask, render_template_string, request, redirect, session, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "mysecretkey"

# -------------------------------
# CONFIG
# -------------------------------
UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"mp4", "webm", "ogg"}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

DATABASE = "website.db"

# -------------------------------
# DATABASE
# -------------------------------
def init_db():
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()

    # USERS TABLE
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        email TEXT UNIQUE,
        password TEXT
    )
    """)

    # VIDEOS TABLE
    cur.execute("""
    CREATE TABLE IF NOT EXISTS videos(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        filename TEXT
    )
    """)

    conn.commit()
    conn.close()

init_db()

# -------------------------------
# ADMIN LOGIN
# -------------------------------
ADMIN_EMAIL = "admin@gmail.com"
ADMIN_PASSWORD = "admin123"

# -------------------------------
# CHECK VIDEO EXTENSION
# -------------------------------
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# -------------------------------
# HOME PAGE
# -------------------------------
@app.route("/")
def home():
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()

    cur.execute("SELECT * FROM videos")
    videos = cur.fetchall()

    conn.close()

    return render_template_string("""
    <html>
    <head>
        <title>YouTube Clone</title>
        <style>
            body{
                font-family: Arial;
                background:#f2f2f2;
                margin:0;
                padding:0;
            }

            .navbar{
                background:red;
                color:white;
                padding:15px;
            }

            .container{
                padding:20px;
            }

            .video-box{
                background:white;
                padding:15px;
                margin-bottom:20px;
                border-radius:10px;
            }

            video{
                width:100%;
                max-width:600px;
            }

            a{
                text-decoration:none;
                color:white;
                margin-right:15px;
            }

            .btn{
                background:red;
                color:white;
                padding:10px;
                border:none;
                border-radius:5px;
            }
        </style>
    </head>

    <body>

        <div class="navbar">
            <h2>YouTube Clone</h2>

            <a href="/">Home</a>

            {% if "user" not in session %}
                <a href="/register">Register</a>
                <a href="/login">Login</a>
            {% else %}
                <a href="/logout">Logout</a>
            {% endif %}

            {% if session.get("user") == ADMIN_EMAIL %}
                <a href="/upload">Upload Video</a>
            {% endif %}
        </div>

        <div class="container">

            <h2>Videos</h2>

            {% for video in videos %}

                <div class="video-box">

                    <h3>{{ video[1] }}</h3>

                    <video controls>
                        <source src="/uploads/{{ video[2] }}" type="video/mp4">
                    </video>

                    {% if session.get("user") == ADMIN_EMAIL %}

                        <br><br>

                        <a class="btn" href="/delete_video/{{ video[0] }}">
                            Delete
                        </a>

                    {% endif %}

                </div>

            {% endfor %}

        </div>

    </body>
    </html>
    """, videos=videos, ADMIN_EMAIL=ADMIN_EMAIL)

# -------------------------------
# REGISTER
# -------------------------------
@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        username = request.form["username"]
        email = request.form["email"]
        password = generate_password_hash(request.form["password"])

        conn = sqlite3.connect(DATABASE)
        cur = conn.cursor()

        try:
            cur.execute("""
            INSERT INTO users(username,email,password)
            VALUES(?,?,?)
            """, (username, email, password))

            conn.commit()

            flash("Registration Successful")
            return redirect("/login")

        except:
            flash("Email already exists")

        conn.close()

    return render_template_string("""
    <html>
    <body style="font-family:Arial;background:#f2f2f2;">

    <div style="width:300px;margin:auto;margin-top:100px;background:white;padding:20px;border-radius:10px;">

        <h2>Register</h2>

        <form method="POST">

            <input type="text" name="username" placeholder="Username" required style="width:100%;padding:10px;"><br><br>

            <input type="email" name="email" placeholder="Email" required style="width:100%;padding:10px;"><br><br>

            <input type="password" name="password" placeholder="Password" required style="width:100%;padding:10px;"><br><br>

            <button type="submit" style="width:100%;padding:10px;background:red;color:white;border:none;">
                Register
            </button>

        </form>

        <br>

        <a href="/login">Already have account?</a>

    </div>

    </body>
    </html>
    """)

# -------------------------------
# LOGIN
# -------------------------------
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        # ADMIN LOGIN
        if email == ADMIN_EMAIL and password == ADMIN_PASSWORD:
            session["user"] = ADMIN_EMAIL
            return redirect("/")

        conn = sqlite3.connect(DATABASE)
        cur = conn.cursor()

        cur.execute("""
        SELECT * FROM users WHERE email=?
        """, (email,))

        user = cur.fetchone()

        conn.close()

        if user and check_password_hash(user[3], password):
            session["user"] = email
            return redirect("/")
        else:
            flash("Invalid Login")

    return render_template_string("""
    <html>
    <body style="font-family:Arial;background:#f2f2f2;">

    <div style="width:300px;margin:auto;margin-top:100px;background:white;padding:20px;border-radius:10px;">

        <h2>Login</h2>

        <form method="POST">

            <input type="email" name="email" placeholder="Email" required style="width:100%;padding:10px;"><br><br>

            <input type="password" name="password" placeholder="Password" required style="width:100%;padding:10px;"><br><br>

            <button type="submit" style="width:100%;padding:10px;background:red;color:white;border:none;">
                Login
            </button>

        </form>

        <br>

        <a href="/register">Create account</a>

    </div>

    </body>
    </html>
    """)

# -------------------------------
# LOGOUT
# -------------------------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# -------------------------------
# VIDEO UPLOAD
# -------------------------------
@app.route("/upload", methods=["GET", "POST"])
def upload():

    if session.get("user") != ADMIN_EMAIL:
        return redirect("/login")

    if request.method == "POST":

        title = request.form["title"]

        if "video" not in request.files:
            return "No file selected"

        file = request.files["video"]

        if file.filename == "":
            return "No file selected"

        if file and allowed_file(file.filename):

            filename = secure_filename(file.filename)

            filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)

            file.save(filepath)

            conn = sqlite3.connect(DATABASE)
            cur = conn.cursor()

            cur.execute("""
            INSERT INTO videos(title,filename)
            VALUES(?,?)
            """, (title, filename))

            conn.commit()
            conn.close()

            return redirect("/")

    return render_template_string("""
    <html>
    <body style="font-family:Arial;background:#f2f2f2;">

    <div style="width:400px;margin:auto;margin-top:100px;background:white;padding:20px;border-radius:10px;">

        <h2>Upload Video</h2>

        <form method="POST" enctype="multipart/form-data">

            <input type="text" name="title" placeholder="Video Title" required style="width:100%;padding:10px;"><br><br>

            <input type="file" name="video" required><br><br>

            <button type="submit" style="width:100%;padding:10px;background:red;color:white;border:none;">
                Upload
            </button>

        </form>

    </div>

    </body>
    </html>
    """)

# -------------------------------
# DELETE VIDEO
# -------------------------------
@app.route("/delete_video/<int:id>")
def delete_video(id):

    if session.get("user") != ADMIN_EMAIL:
        return redirect("/login")

    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()

    cur.execute("SELECT filename FROM videos WHERE id=?", (id,))
    video = cur.fetchone()

    if video:

        filepath = os.path.join(app.config["UPLOAD_FOLDER"], video[0])

        if os.path.exists(filepath):
            os.remove(filepath)

        cur.execute("DELETE FROM videos WHERE id=?", (id,))
        conn.commit()

    conn.close()

    return redirect("/")

# -------------------------------
# SHOW UPLOADED VIDEOS
# -------------------------------
@app.route("/uploads/<filename>")
def uploaded_file(filename):
    from flask import send_from_directory
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

# -------------------------------
# MAIN
# -------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)