from werkzeug.security import check_password_hash, generate_password_hash
from db import query
import db
import re

def validate_password_strength(password):
    if len(password) < 8:
        return False, "Salasanan pituus tulee olla vähintään 8 merkkiä."
    
    if not re.search(r"[A-Z]", password):
        return False, "Salasanassa täytyy olla vähintään yksi iso kirjain."
    
    if not re.search(r"[a-z]", password):
        return False, "Salasanassa täytyy olla vähintään yksi pieni kirjain."
    
    if not re.search(r"[0-9]", password):
        return False, "Salasanassa täytyy olla vähintään yksi numero."
    
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False, "Salasanassa täytyy olla vähintään yksi erikoismerkki."
    
    return True, "Salasana on vahva."

def create_user(username, password_hash):
    sql = "SELECT id FROM users WHERE username = ?"
    result = db.query(sql, [username])
    if result:
        raise ValueError("Tunnus on jo varattu.")
    
    sql = "INSERT INTO users (username, password_hash) VALUES (?, ?)"
    db.execute(sql, [username, password_hash])

def check_login(username, password):
    sql = "SELECT id, password_hash FROM users WHERE username = ?"
    result = db.query(sql, [username])
    
    if not result:
        return None
    
    user_id = result[0]["id"]
    password_hash = result[0]["password_hash"]
    if check_password_hash(password_hash, password):
        return user_id
    else:
        return None

def get_user(user_id):
    sql = """SELECT id, username, image IS NOT NULL AS has_image
             FROM users WHERE id = ?"""
    result = db.query(sql, [user_id])
    return result[0] if result else None

def get_items(user_id):
    sql = "SELECT id, title FROM items WHERE user_id = ? ORDER BY id DESC"
    return db.query(sql, [user_id])

def get_user_by_username(username):
    sql = "SELECT id, username, password_hash FROM users WHERE username = ?"
    result = db.query(sql, [username])
    
    if result:
        return result[0]
    return None

def update_user(user_id, new_username, new_password):
    sql = "SELECT id FROM users WHERE username = ?"
    result = db.query(sql, [new_username])
    
    if result:
        raise ValueError("Käyttäjätunnus on jo varattu.")

    new_password_hash = generate_password_hash(new_password)
    
    sql = """UPDATE users
             SET username = ?, password_hash = ?
             WHERE id = ?"""
    db.execute(sql, [new_username, new_password_hash, user_id])

def update_image(user_id, image):
    sql = "UPDATE users SET image = ? WHERE id = ?"
    db.execute(sql, [image, user_id])
    
def get_image(user_id):
    sql = "SELECT image FROM users WHERE id = ?"
    result = db.query(sql, [user_id])
    return result[0]["image"] if result else None

def get_messages(user_id):
    sql = """
    SELECT m.id,
           m.content,
           m.sent_at,
           m.thread_id,
           i.title AS item_title,
           i.id AS item_id,
           u.username AS sender
    FROM messages m
    JOIN message_threads t ON m.thread_id = t.id
    JOIN items i ON m.item_id = i.id
    JOIN users u ON m.sender_id = u.id
    WHERE t.sender_id = ? OR t.recipient_id = ?
    ORDER BY m.sent_at DESC
    """
    return db.query(sql, [user_id, user_id])

def get_message_thread(thread_id):
    sql = """
    SELECT m.content, m.sent_at, u.username
    FROM messages m
    JOIN users u ON m.sender_id = u.id
    WHERE m.thread_id = ?
    ORDER BY m.sent_at ASC
    """
    return db.query(sql, [thread_id])

def create_user_with_validation(username, password1, password2):
    if password1 != password2:
        raise ValueError("Salasanat eivät ole samat.")

    is_valid, message = validate_password_strength(password1)
    if not is_valid:
        raise ValueError(message)
        
    password_hash = generate_password_hash(password1)
    create_user(username, password_hash)

def send_message(thread_id, sender_id, recipient_id, content, item_id):
    sql = """
    INSERT INTO messages (thread_id, sender_id, recipient_id, content, item_id)
    VALUES (?, ?, ?, ?, ?)
    """
    db.execute(sql, [thread_id, sender_id, recipient_id, content, item_id])

def get_messages_for_user(user_id):
    sql = """
    SELECT
        m.content,
        m.sent_at,
        u.username,
        CASE
            WHEN t.sender_id = ? THEN (SELECT username FROM users WHERE id = t.recipient_id)
            ELSE (SELECT username FROM users WHERE id = t.sender_id)
        END AS other_user
    FROM messages m
    JOIN message_threads t ON m.thread_id = t.id
    JOIN users u ON m.user_id = u.id
    WHERE t.sender_id = ? OR t.recipient_id = ?
    ORDER BY m.sent_at DESC
    """
    
    rows = query(sql, [user_id, user_id, user_id])

    return rows

def get_messages_by_thread(thread_id):
    sql = """
    SELECT m.content, m.sent_at, u.username, m.thread_id, i.title AS item_title, m.item_id, u.id AS sender_id
    FROM messages m
    JOIN message_threads t ON m.thread_id = t.id
    JOIN users u ON m.sender_id = u.id
    JOIN items i ON m.item_id = i.id
    WHERE m.thread_id = ?
    ORDER BY m.sent_at
    """
    return query(sql, [thread_id])

