import sqlite3

def setup_database():
    """Initializes the SQLite database and creates the necessary tables."""
    DB_NAME = 'ProcRequests.db'
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # 1. Requests Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS requests (
        request_id INTEGER PRIMARY KEY AUTOINCREMENT,
        requestor_name TEXT NOT NULL,
        title TEXT NOT NULL,
        vendor_name TEXT,
        vat_id TEXT,
        commodity_group TEXT,
        department TEXT NOT NULL,
        total_cost REAL,
        status TEXT NOT NULL, -- Open, In Progress, Closed
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 2. Order Lines Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS order_lines (
        line_id INTEGER PRIMARY KEY AUTOINCREMENT,
        request_id INTEGER,
        description TEXT NOT NULL,
        unit_price REAL NOT NULL,
        amount REAL NOT NULL,
        unit TEXT,
        total_price REAL NOT NULL,
        FOREIGN KEY (request_id) REFERENCES requests(request_id)
    );
    """)

    # 3. Status History Table (Audit Trail)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS status_history (
        history_id INTEGER PRIMARY KEY AUTOINCREMENT,
        request_id INTEGER,
        old_status TEXT,
        new_status TEXT NOT NULL,
        changer_user TEXT,
        change_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (request_id) REFERENCES requests(request_id)
    );
    """)

    conn.commit()
    conn.close()
    print("Database setup complete.")

if __name__ == '__main__':
    setup_database()