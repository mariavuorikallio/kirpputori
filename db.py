import sqlite3
from flask import g

DATABASE = 'database.db'

def get_connection():
    """
    Luo ja palauttaa tietokantayhteyden. 
    Käyttää Flaskin g-objektia yhteyksien hallintaan pyynnön elinkaaren ajan.
    """
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.execute("PRAGMA foreign_keys = ON") 
        g.db.row_factory = sqlite3.Row  
    return g.db

def close_connection(exception=None):
    """
    Sulkee tietokannan yhteyden, jos se on avattu.
    Tämä on tarkoitettu käytettäväksi Flaskin `teardown`-koristeluissa.
    """
    db = g.pop('db', None)
    if db is not None:
        db.close()

def execute(sql, params=[]):
    """
    Suorittaa SQL-lauseen tietokantaan.
    """
    con = get_connection()  
    result = con.execute(sql, params)
    con.commit()
    g.last_insert_id = result.lastrowid  
    return result  

def last_insert_id():
    """
    Palauttaa viimeksi lisätyn rivin ID:n.
    """
    return getattr(g, 'last_insert_id', None)

def query(sql, params=[]):
    """
    Suorittaa SELECT-kyselyn ja palauttaa tulokset.
    """
    con = get_connection() 
    result = con.execute(sql, params).fetchall() 
    return result

def init_app(app):
    app.teardown_appcontext(close_connection)

