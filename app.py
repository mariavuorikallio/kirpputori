import sqlite3
from flask import Flask, redirect, render_template, request, session, flash, url_for, abort, make_response
from werkzeug.security import check_password_hash, generate_password_hash
import config
import db
import items
import users
import re
from forum import Forum
from messages import get_messages_for_user

forum = Forum()
app = Flask(__name__)
app.secret_key = config.secret_key

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
        return "VIRHE: väärä tiedostomuoto"

    image = file.read()
    if len(image) > 100 * 1024:
        return "VIRHE: liian suuri kuva"

    user_id = session["user_id"]
    users.update_image(user_id, image)
    return redirect("/user/" + str(user_id))

@app.route("/image/<int:user_id>")
def show_image(user_id):
    image = users.get_image(user_id)
    if not image:
        abort(404)

    response = make_response(bytes(image))
    response.headers.set("Content-Type", "image/jpeg")
    return response

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
    else:
        messages = []

    if request.method == "POST" and "user_id" in session:
        content = request.form["content"]
        sender_id = session["user_id"]
        recipient_id = item["user_id"]

        thread = forum.get_or_create_thread(item_id, sender_id, recipient_id)
        forum.add_message(content, sender_id, thread["id"])

        return redirect(url_for("view_thread", thread_id=thread["id"]))

    return render_template("show_item.html", item=item, messages=messages, classes=classes)

@app.route("/new_item")
def new_item():
    require_login()
    classes = items.get_all_classes()
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

    if not price or not re.match("^[1-9][0-9]{0,3}$", price):
        flash("Hinta on pakollinen ja sen tulee olla välillä 1-9999", "error")
        return redirect(url_for('edit_item', item_id=item_id))

    try:
        price = float(price)
    except ValueError:
        flash("Virheellinen hinta", "error")
        return redirect(url_for('edit_item', item_id=item_id))

    try:
        items.update_item(item_id, title, description, price, condition)
        flash("Ilmoitus päivitetty onnistuneesti", "success")
        return redirect(f"/item/{item_id}")
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

    thread = db.query("SELECT * FROM message_threads WHERE id = ?", [thread_id])
    if not thread:
        abort(404)

    thread = thread[0]

    if current_user not in (thread["sender_id"], thread["recipient_id"]):
        abort(403)

    messages = db.query("""
        SELECT messages.content, messages.sent_at, users.username
        FROM messages
        JOIN users ON messages.user_id = users.id
        WHERE thread_id = ?
        ORDER BY messages.sent_at
    """, [thread_id])

    if request.method == "POST":
        content = request.form["content"]
        if content.strip():
            db.execute(
                "INSERT INTO messages (content, user_id, thread_id) VALUES (?, ?, ?)",
                [content, current_user, thread_id]
            )
            return redirect(url_for("view_thread", thread_id=thread_id))

    return render_template("view_thread.html", messages=messages, thread=thread)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password1 = request.form["password1"]
        password2 = request.form["password2"]

        if password1 != password2:
            flash("Salasanat eivät ole samat", "error")
            return redirect(url_for('register'))

        is_valid, message = users.validate_password_strength(password1)
        if not is_valid:
            flash(message, "error")
            return redirect(url_for('register'))

        password_hash = generate_password_hash(password1)

        try:
            users.create_user(username, password_hash)
        except sqlite3.IntegrityError:
            flash("Tunnus on jo varattu", "error")
            return redirect(url_for('register'))
        except ValueError as e:
            flash(str(e), "error")
            return redirect(url_for('register'))

        flash("Tunnus luotu onnistuneesti", "success")
        return redirect(url_for('login'))

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect("/")

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        user = users.get_user_by_username(username)
        if not user:
            flash("Käyttäjätunnusta ei löydy", "error")
            return redirect(url_for('login'))

        if check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            flash("Tervetuloa takaisin!", "success")
            return redirect("/")
        else:
            flash("Väärä tunnus tai salasana", "error")
            return redirect(url_for('login'))

    return render_template("login.html")

@app.route("/logout")
def logout():
    if "user_id" in session:
        session.pop("user_id", None)
        session.pop("username", None)
        flash("Olet kirjautunut ulos", "success")
    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True, host='127.0.0.1', port=5001)


