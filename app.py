import sqlite3
from flask import abort, Flask, redirect, render_template, request, session, flash, url_for
from werkzeug.security import check_password_hash, generate_password_hash
import config
import db
import items
import re
import users
from users import create_user, get_user_by_username
from datetime import datetime

app = Flask(__name__)
app.secret_key = config.secret_key

db.init_app(app)

def require_login():
    if "user_id" not in session:
        abort(403)

@app.route("/")
def index():
    all_items = items.get_items()
    return render_template("index.html", items=all_items)

@app.route('/user/<int:user_id>', methods=['GET'])
def show_user(user_id):
    user = users.get_user(user_id)
    if user:
        items = users.get_items(user_id)
        return render_template('show_user.html', user=user, items=items)
    else:
        print(f"User {user_id} not found")
        return "User not found", 404

@app.route("/find_item")
def find_item():
    query = request.args.get("query")
    results = []

    if query:
        results = items.find_items(query)

    return render_template("find_item.html", query=query, results=results)

@app.route("/item/<int:item_id>")
def show_item(item_id):
    item = items.get_item(item_id)

    if item is None:
        flash(f"Tavaraa id {item_id} ei löytynyt", "error")
        return redirect("/")
    classes = items.get_classes(item_id)
    return render_template("show_item.html", item=item, classes=classes)

@app.route("/new_item")
def new_item():
    require_login()
    return render_template("new_item.html")

@app.route("/create_item", methods=["POST"])
def create_item():
    require_login()

    title = request.form["title"]
    description = request.form["description"]
    price = request.form["price"]
    condition = request.form["condition"]
    section = request.form["section"]
    classes = request.form.getlist("classes")
    
    last_modified = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    if not title or len(title) > 50:
        flash("Otsikko on pakollinen ja enintään 50 merkkiä pitkä", "error")
        return redirect(url_for('new_item'))

    if not description or len(description) > 1000:
        flash("Kuvaus on pakollinen ja enintään 1000 merkkiä pitkä", "error")
        return redirect(url_for('new_item'))

    if not price or not re.match("^[1-9][0-9]{0,3}$", price):
        flash("Hinta on pakollinen ja sen tulee olla välillä 1-9999", "error")
        return redirect(url_for('new_item'))

    try:
        price = int(price)  
        if price < 1 or price > 9999:
            raise ValueError("Hinta ei ole kelvollinen")
    except ValueError:
        flash("Virheellinen hinta", "error")
        return redirect(url_for('new_item'))

    if not condition or not section:
        flash("Kunto ja osasto ovat pakollisia", "error")
        return redirect(url_for('new_item'))

    user_id = session["user_id"]

    try:
        items.add_item(title, description, price, condition, user_id, section, classes)
        flash("Tavara lisätty onnistuneesti", "success")
        return redirect("/") 
    except Exception as e:
        flash(f"Virhe lisäyksessä: {str(e)}", "error")
        return redirect(url_for('new_item'))  

@app.route("/edit_item/<int:item_id>")
def edit_item(item_id):
    require_login()
    item = items.get_item(item_id)
    if not item:
        abort(404)
    if item["user_id"] != session["user_id"]:
        abort(403)
    return render_template("edit_item.html", item=item)
    
    last_modified = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

@app.route("/update_item", methods=["POST"])
def update_item():
    item_id = request.form.get("item_id")
    item = items.get_item(item_id)

    if not item:
        abort(404)
    if item["user_id"] != session["user_id"]:
        abort(403)

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

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password1 = request.form["password1"]
        password2 = request.form["password2"]

        if password1 != password2:
            flash("Salasanat eivät ole samat", "error")
            return redirect(url_for('register'))

        password_hash = generate_password_hash(password1)

        try:
            create_user(username, password_hash)

        except sqlite3.IntegrityError:
            flash("Tunnus on jo varattu", "error")
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

        user = get_user_by_username(username)
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
