from db import init_db, init_app
from flask import Flask

app = Flask(__name__)
init_app(app)

with app.app_context():
    init_db()
    print("Tietokanta alustettu!")

