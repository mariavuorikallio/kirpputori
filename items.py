import db

def add_item(title, description, start_price, user_id):
    sql = """INSERT INTO items (title, description, start_price, user_id) VALUES (?, ?, ?, ?)"""
    db.execute(sql, [title, description, start_price, user_id])

def get_items():
    sql = "SELECT id, title FROM items ORDER BY id DESC"
    return db.query(sql)

def get_item(item_id):
    sql = """SELECT items.title,
                    items.description,
                    items.start_price,
                    users.username
             FROM items
             JOIN users ON items.user_id = users.id
             WHERE items.id = ?"""
    return db.query(sql, [item_id])[0]

