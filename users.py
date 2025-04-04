from werkzeug.security import check_password_hash, generate_password_hash

import db

def create_user(username, password_hash):
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
    sql = "SELECT id, username FROM users WHERE id = ?"
    result = db.query(sql, [user_id])
    if result:
        return result[0] 
    else:
        return None 
        
def get_user_by_username(username):
    sql = "SELECT id, username, password_hash FROM users WHERE username = ?"
    result = db.query(sql, [username])  
    if result:
        return result[0]
    return None  
        
def get_items(user_id):
    sql =  "SELECT id, title FROM items WHERE user_id = ? ORDER BY id DESC"
    return db.query(sql, [user_id])
    
       

