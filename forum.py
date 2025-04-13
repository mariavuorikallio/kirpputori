from flask import session
import db

class Forum:
    def get_messages_for_item(self, item_id):
        sql = """SELECT m.id, m.content, m.sent_at, u.username, m.user_id
                 FROM messages m 
                 JOIN users u ON m.user_id = u.id
                 WHERE m.item_id = ?"""
        return db.query(sql, [item_id])

    def get_or_create_thread(self, item_id, sender_id, recipient_id):
        sql = """
            SELECT * FROM message_threads
            WHERE item_id = ? AND (
                (sender_id = ? AND recipient_id = ?) OR
                (sender_id = ? AND recipient_id = ?)
            )
        """
        thread = db.query_one(sql, [item_id, sender_id, recipient_id, recipient_id, sender_id])

        if thread:
            return thread

        db.execute("""INSERT INTO message_threads (item_id, sender_id, recipient_id)
                      VALUES (?, ?, ?)""", [item_id, sender_id, recipient_id])

        return db.query_one(sql, [item_id, sender_id, recipient_id, recipient_id, sender_id])

    def add_message(self, content, user_id, thread_id):
        sql = """INSERT INTO messages (content, user_id, thread_id) 
                 VALUES (?, ?, ?)"""
        db.execute(sql, [content, user_id, thread_id])
        
        print(f"Message added: content={content}, user_id={user_id}, thread_id={thread_id}")

