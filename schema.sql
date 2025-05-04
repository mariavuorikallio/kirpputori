CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    price REAL NOT NULL,
    condition TEXT NOT NULL,
    section TEXT NOT NULL,
    created_at TEXT NOT NULL,
    last_modified TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS items_classes (
    item_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    value TEXT NOT NULL,
    FOREIGN KEY (item_id) REFERENCES items(id)
);

CREATE TABLE IF NOT EXISTS classes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    value TEXT
);

CREATE TABLE IF NOT EXISTS message_threads (
    id INTEGER PRIMARY KEY,
    item_id INTEGER REFERENCES items,
    sender_id INTEGER REFERENCES users,
    recipient_id INTEGER REFERENCES users
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY,
    thread_id INTEGER REFERENCES message_threads,
    content TEXT,
    sent_at TEXT DEFAULT CURRENT_TIMESTAMP,
    user_id INTEGER REFERENCES users
);


