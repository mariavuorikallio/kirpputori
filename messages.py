from db import query  

def get_messages_for_user(user_id):
    sql = """
    SELECT m.id,
           m.content,
           m.sent_at,
           m.thread_id,
           i.title AS item_title
    FROM messages m
    JOIN message_threads t ON m.thread_id = t.id
    JOIN items i ON m.item_id = i.id
    WHERE t.sender_id = ? OR t.recipient_id = ?
    ORDER BY m.sent_at DESC
    """
    rows = query(sql, [user_id, user_id])

    messages = [dict(row) for row in rows]
    
    return messages

