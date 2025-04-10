from flask import session
import db
from datetime import datetime

def add_item(title, description, price, condition, user_id, section, classes):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sql = """INSERT INTO items (title, description, price, condition, user_id, section, last_modified)
             VALUES (?, ?, ?, ?, ?, ?, ?)"""
    db.execute(sql, [title, description, price, condition, user_id, section, now])
    
    item_id = db.last_insert_id()
    
    sql = "INSERT INTO items_classes (item_id, title, value) VALUES (?, ?, ?)"
    
    db.execute(sql, [item_id, "Osasto", section])
    
    db.execute(sql, [item_id, "Kunto", condition])
    
    for class_title, value in classes:
        db.execute(sql, [item_id, class_title, value])
      
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
             FROM items, users
             WHERE items.user_id = users.id AND
                   items.id = ?"""
    result = db.query(sql, [item_id])

    if result:
        return result[0]
    else:
        return None

def update_item(item_id, title, description, price, condition):
    user_id = session.get("user_id")

    if not user_id:
        raise ValueError("User is not logged in")
        
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sql = """UPDATE items
               SET title = ?, description = ?, price = ?, condition = ?, last_modified = ?
               WHERE id = ? AND user_id = ?"""
    db.execute(sql, [title, description, price, condition, item_id, user_id])

def remove_item(item_id):
    sql = "DELETE FROM items WHERE id = ?"
    db.execute(sql, [item_id])

def find_items(query):
    sql = """SELECT id, title
             FROM items
             WHERE title LIKE ? OR description LIKE ?
             ORDER BY id DESC"""
    like = "%" + query + "%"
    return db.query(sql, [like, like])
