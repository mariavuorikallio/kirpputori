import sqlite3
from flask import Flask, redirect, render_template, request, session, flash, url_for, abort, make_response, get_flashed_messages
from werkzeug.security import check_password_hash, generate_password_hash
import config
import db
import items
import users
import re
from db import query, get_user_messages
from forum import Forum
from flask_wtf.csrf import CSRFProtect
from users import get_messages_for_user, get_messages_by_thread
import random  
import string

forum = Forum()
app = Flask(__name__)
app.secret_key = config.secret_key
app.config['SECRET_KEY'] = 'mysecretkey'
csrf = CSRFProtect(app)

def generate_csrf_token():
    token = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
    session['csrf_token'] = token
    return token

@app.before_request
def before_request():
    if 'csrf_token' not in session:
        generate_csrf_token()
        
def validate_csrf_token():
    token = session.get('csrf_token')
    form_token = request.form.get('csrf_token')
    if not form_token or form_token != token:
        flash("CSRF token on virheellinen tai puuttuu!", 'error')
        return False
    return True

def require_login():
    if "user_id" not in session:
        flash("Sinun täytyy olla kirjautunut sisään, jotta voit jatkaa", "error")
        return redirect(url_for('login'))

@app.route("/")
def index():
    all_items = items.get_items()
    return render_template("index.html", items=all_items)

@app.route("/user/<int:user_id>", methods=['GET'])
def show_user(user_id):
    user = users.get_user(user_id)
    if not user:
        app.logger.warning(f"User {user_id} not found")
        abort(404)

    user_items = users.get_items(user_id)
    messages = get_messages_for_user(user_id)

    print(f"Messages for user {user_id}: {messages}")

    return render_template('show_user.html', user=user, user_items=user_items, messages=messages)

@app.route("/add_image", methods=["GET", "POST"])
def add_image():
    require_login()

    if request.method == "GET":
        return render_template("add_image.html")

    file = request.files["image"]
    if not file.filename.endswith(".jpg"):
        flash("VIRHE: väärä tiedostomuoto", "error")
        return render_template("add_image.html")

    image = file.read()
    if len(image) > 100 * 1024:
        flash("VIRHE: liian suuri kuva", "error")
        return render_template("add_image.html")

    user_id = session["user_id"]
    users.update_image(user_id, image)
    return redirect(url_for('show_user', user_id=user_id))

@app.route("/image/<int:user_id>")
def show_image(user_id):
    image = users.get_image(user_id)
    if not image:
        abort(404)

    response = make_response(bytes(image))
    response.headers.set("Content-Type", "image/jpeg")
    return response
    
@app.route('/profile/edit')
def edit_profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_id = session['user_id']
    user = db.query("SELECT id, username FROM users WHERE id = ?", [user_id])[0]
    flashed_messages = get_flashed_messages(with_categories=True)
    print(f"Flashed messages edit_profile: {flashed_messages}")
    return render_template('edit_profile.html', user=user)

@app.route('/profile/update', methods=['POST'])
def update_profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_id = session['user_id']
    flash('Profiili päivitetty onnistuneesti!', 'success')
    return redirect(url_for('show_user', user_id=user_id))


@app.route("/find_item")
def find_item():
    query = request.args.get("query")
    results = []

    if query:
        results = items.find_items(query)

    return render_template("find_item.html", query=query, results=results)

@app.route("/item/<int:item_id>", methods=["GET", "POST"])
def show_item(item_id):
    item = items.get_item(item_id)
    if not item:
        abort(404)

    classes = items.get_classes(item_id)
    user_id = item["user_id"]

    messages = []
    thread_id = None

    if "user_id" in session:
        thread = forum.get_or_create_thread(item_id, session["user_id"], user_id)
        thread_id = thread["id"]

        messages = db.query("""
            SELECT messages.content, messages.sent_at, users.username
            FROM messages
            JOIN users ON messages.user_id = users.id
            WHERE thread_id = ?
            ORDER BY messages.sent_at
        """, [thread_id])

    if request.method == "POST" and "user_id" in session:
        content = request.form["content"]
        sender_id = session["user_id"]
        recipient_id = item["user_id"]

        thread = forum.get_or_create_thread(item_id, sender_id, recipient_id)
        forum.add_message(content, sender_id, thread["id"])

        return redirect(url_for("view_thread", thread_id=thread["id"]))

    return render_template("show_item.html", item=item, messages=messages, classes=classes, thread_id=thread_id)
    
@app.route("/new_item")
def new_item():
    require_login()
    classes = items.get_all_classes()
    print(f"Luokat (new_item): {classes}")
    return render_template("new_item.html", classes=classes)

@app.route("/create_item", methods=["POST"])
def create_item():
    require_login()

    print("--- CREATE ITEM CALLED ---")
    print(f"Session: {session}")
    print(f"Form data: {request.form}")

    title = request.form["title"]
    description = request.form["description"]
    price = request.form["price"]

    print(f"Form data keys: {list(request.form.keys())}")

    section = request.form.get("classes[Osasto]")
    condition = request.form.get("classes[Kunto]")

    print(f"Extracted Section: {section}, Condition: {condition}")

    if not section or not condition:
        flash("Osasto ja Kunto ovat pakollisia", "error")
        return redirect(url_for('new_item'))

    classes_to_pass = [("Osasto", section), ("Kunto", condition)]

    print(f"Classes to pass: {classes_to_pass}")

    try:
        price = float(price)
    except ValueError:
        flash("Virheellinen hinta", "error")
        return redirect(url_for('new_item'))

    user_id = session["user_id"]

    try:
        items.add_item(title, description, price, condition, user_id, section, classes_to_pass)
        flash("Tavara lisätty onnistuneesti", "success")
        return redirect("/")
    except sqlite3.OperationalError as e:
        if "no such table: items_classes" in str(e):
            flash("VIRHE: Tietokantataulu 'items_classes' puuttuu. Ota yhteyttä ylläpitäjään.", "error")
        else:
            flash(f"Virhe lisäyksessä: {str(e)}", "error")
        return redirect(url_for('new_item'))
    except ValueError as e:
        flash(str(e), "error")
        return redirect(url_for('new_item'))
    except Exception as e:
        flash(f"Virhe lisäyksessä: {str(e)}", "error")
        return redirect(url_for('new_item'))

@app.route("/update_item", methods=["POST"])
def update_item():
    item_id = request.form.get("item_id")
    item = items.get_item(item_id)

    if not item:
        abort(404)
    if item["user_id"] != session["user_id"]:
        abort(403)

    classes = []
    for entry in request.form.getlist("classes"):
        if entry:
            parts = entry.split(":")
            classes.append((parts[0], parts[1]))

    title = request.form.get("title")
    description = request.form.get("description")
    price = request.form.get("price")
    condition = request.form.get("condition")

    if not title or len(title) > 50:
        flash("Otsikko on pakollinen ja enintään 50 merkkiä pitkä", "error")
        return redirect(url_for('edit_item', item_id=item_id))

    if not description or len(description) > 1000:
        flash("Kuvaus on pakollinen ja enintään 1000 merkkiä pitkä", "error")
        return redirect(url_for('edit_item', item_id=item_id))

    if not price or not re.match(r"^[1-9][0-9]{0,3}$", price):
        flash("Hinta on pakollinen ja sen tulee olla välillä 1-9999", "error")
        return redirect(url_for('edit_item', item_id=item_id))

    try:
        price = float(price)
    except ValueError:
        flash("Virheellinen hinta", "error")
        return redirect(url_for('edit_item', item_id=item_id))

    try:
        items.update_item(item_id, title, description, price, condition, classes)
        flash("Ilmoitus päivitetty onnistuneesti", "success")
        return redirect(f"/item/{item_id}")
    except ValueError as e:
        flash(str(e), "error")
        return redirect(url_for('edit_item', item_id=item_id))
    except Exception as e:
        app.logger.error(f"Virhe päivityksessä: {str(e)}")
        flash(f"Virhe päivityksessä: {str(e)}", "error")
        return redirect(url_for('edit_item', item_id=item_id))

@app.route("/remove_item/<int:item_id>", methods=["GET", "POST"])
def remove_item(item_id):
    require_login()
    item = items.get_item(item_id)
    if not item:
        abort(404)
    if item["user_id"] != session["user_id"]:
        abort(403)

    if request.method == "GET":
        return render_template("remove_item.html", item=item)

    if request.method == "POST":
        if "remove" in request.form:
            items.remove_item(item_id)
            return redirect("/")
        else:
            return redirect(f"/item/{item_id}")

@app.route("/thread/<int:thread_id>", methods=["GET", "POST"])
def view_thread(thread_id):
    if "user_id" not in session:
        flash("Kirjaudu sisään nähdäksesi viestiketjut", "error")
        return redirect(url_for('login'))

    current_user = session["user_id"]

    thread = db.query_one("SELECT * FROM message_threads WHERE id = ?", [thread_id])
    if not thread:
        abort(404)

    if current_user not in (thread["sender_id"], thread["recipient_id"]):
        abort(403)

    recipient = db.query_one("SELECT username FROM users WHERE id = ?", [thread["recipient_id"]])
    thread["recipient_username"] = recipient["username"]

    messages = db.query("""
        SELECT messages.content, messages.sent_at, users.username
        FROM messages
        JOIN users ON messages.user_id = users.id
        WHERE thread_id = ?
        ORDER BY messages.sent_at
    """, [thread_id])

    if request.method == "POST":
        token = session.get('csrf_token')
        form_token = request.form.get('csrf_token')
        if not form_token or form_token != token:
            flash("CSRF-token on virheellinen tai puuttuu", "error")
            return redirect(url_for("view_thread", thread_id=thread_id))

        content = request.form["content"]
        if content.strip():
            db.execute(
                "INSERT INTO messages (content, user_id, thread_id) VALUES (?, ?, ?)",
                [current_user, content, thread_id]
            )
            flash("Viestisi on lähetetty", "success")
            return redirect(url_for("view_thread", thread_id=thread_id))

    return render_template("view_thread.html", messages=messages, thread=thread, csrf_token=session.get('csrf_token'))
    
@app.route("/message_thread/<int:thread_id>")
def message_thread(thread_id):
    print(f"Viestiketju {thread_id} haetaan...")
    thread_messages = get_messages_by_thread(thread_id)

    if not thread_messages:
        flash("Viestiketjua ei löytynyt.", "error")
        return redirect(url_for("index"))

    print(f"Viestiketjun viestit: {thread_messages}")  
    return render_template("message_thread.html", messages=thread_messages)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        password_hash = generate_password_hash(password)
        if users.add_user(username, password_hash):
            flash("Rekisteröityminen onnistui. Voit nyt kirjautua sisään.", "success")
            return redirect(url_for("login"))
        else:
            flash("Käyttäjänimi on jo käytössä.", "error")
            return render_template("register.html")
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = users.get_user_by_username(username)
        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"] 
            flash("Kirjautuminen onnistui.", "success")
            return redirect(url_for("index"))
        else:
            flash("Virheellinen käyttäjänimi tai salasana", "error")
    return render_template("login.html")

@app.route("/logout")
def logout():
    print(f"Before logout: {session}")
    session.pop("user_id", None)
    session.pop("username", None) 
    session.pop("csrf_token", None) 
    print(f"After logout: {session}")
    flash("Olet kirjautunut ulos.", "success")
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)

