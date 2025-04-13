from flask import session
import db
from datetime import datetime

def get_all_classes():
    sql = "SELECT title, value FROM classes ORDER BY id"
    result = db.query(sql)
    
    classes = {} 
    for title, value in result:
        if title not in classes:
            classes[title] = []
        classes[title].append(value)
        
    return classes

def get_classes(item_id):
    sql = "SELECT title, value FROM items_classes WHERE item_id = ?"
    return db.query(sql, [item_id])

def get_items():
    sql = "SELECT id, title FROM items ORDER BY id DESC"
    return db.query(sql)

def get_item(item_id):
    sql = """SELECT items.id,
                    items.title,
                    items.description,
                    items.price,
                    items.condition,
                    items.last_modified,
                    users.id user_id,
                    users.username
             FROM items
             JOIN users ON items.user_id = users.id
             WHERE items.id = ?"""
    result = db.query(sql, [item_id])
    if result:
        return result[0]
    return None

def add_item(title, description, price, condition, user_id, section, classes):
    if not title or len(title) < 3:
        raise ValueError("Otsikko on pakollinen ja vähintään 3 merkkiä pitkä.")
    if not description or len(description) < 10:
        raise ValueError("Kuvaus on pakollinen ja vähintään 10 merkkiä pitkä.")
    if not (0 < price < 10000):
        raise ValueError("Hinta on pakollinen ja sen tulee olla välillä 1-9999.")
    
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    sql = """INSERT INTO items (title, description, price, condition, user_id, section, created_at, last_modified)
             VALUES (?, ?, ?, ?, ?, ?, ?, ?)"""
    db.execute(sql, [title, description, price, condition, user_id, section, now, now])  

    item_id = db.last_insert_id()  

    sql = "INSERT INTO items_classes (item_id, title, value) VALUES (?, ?, ?)"
    for title, value in classes:
        db.execute(sql, [item_id, title, value])

def update_item(item_id, title, description, price, condition, classes):
    if not title or len(title) < 3:
        raise ValueError("Otsikko on pakollinen ja vähintään 3 merkkiä pitkä.")
    if not description or len(description) < 10:
        raise ValueError("Kuvaus on pakollinen ja vähintään 10 merkkiä pitkä.")
    if not (0 < price < 10000):
        raise ValueError("Hinta on pakollinen ja sen tulee olla välillä 1-9999.")
    
    user_id = session.get("user_id")

    if not user_id:
        raise ValueError("Et ole kirjautunut sisään.")
    
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    sql = """UPDATE items
               SET title = ?, description = ?, price = ?, condition = ?, last_modified = ?
               WHERE id = ? AND user_id = ?"""
    db.execute(sql, [title, description, price, condition, now, item_id, user_id])

    sql = "DELETE FROM items_classes WHERE item_id = ?"
    db.execute(sql, [item_id])
    
    sql = "INSERT INTO items_classes (item_id, title, value) VALUES (?, ?, ?)"
    for title, value in classes:
        db.execute(sql, [item_id, title, value])

        
def remove_item(item_id):
    sql = "DELETE FROM items WHERE id = ?"
    db.execute(sql, [item_id])
    
def get_or_create_thread(item_id, sender_id, recipient_id):
    sql = """SELECT id FROM message_threads 
             WHERE item_id = ? AND sender_id = ? AND recipient_id = ?"""
    thread = db.query(sql, [item_id, sender_id, recipient_id])
    
    if thread:
        return thread[0]  
    else:
        sql = """INSERT INTO message_threads (item_id, sender_id, recipient_id)
                 VALUES (?, ?, ?)"""
        db.execute(sql, [item_id, sender_id, recipient_id])
        return {"id": db.last_insert_id()}  

def get_messages_for_item(item_id):
    sql = """SELECT m.id, m.content, m.sent_at, u.username, m.user_id
             FROM messages m JOIN users u ON m.user_id = u.id
             JOIN message_threads t ON t.id = m.thread_id
             WHERE t.item_id = ?"""
    return db.query(sql, [item_id])

def add_message(content, user_id, thread_id):
    sql = """INSERT INTO messages (content, user_id, thread_id) 
             VALUES (?, ?, ?)"""
    db.execute(sql, [content, user_id, thread_id])

def find_items(query):
    sql = """SELECT id, title
             FROM items
             WHERE title LIKE ? OR description LIKE ?
             ORDER BY id DESC"""
    like = "%" + query + "%"
    return db.query(sql, [like, like])
   
