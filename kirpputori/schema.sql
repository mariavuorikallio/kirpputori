CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    username TEXT UNIQUE,
    password_hash TEXT
);

CREATE TABLE items (
    id INTEGER PRIMARY KEY,
    title TEXT,
    description TEXT,
    price INTEGER,
    user_id INTEGER REFERENCES users(id),
    condition TEXT DEFAULT 'uusi' CHECK(condition IN ('uusi', 'hyvä', 'kohtalainen')), 
    last_modified DATETIME DEFAULT CURRENT_TIMESTAMP  
);

