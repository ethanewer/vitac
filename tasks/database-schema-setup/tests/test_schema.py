import os
import sqlite3

DB_PATH = "/app/data/app.db"

def _conn():
    assert os.path.exists(DB_PATH), f"Database not found at {DB_PATH}"
    return sqlite3.connect(DB_PATH)

def test_database_exists():
    assert os.path.exists(DB_PATH)

def test_categories_table():
    conn = _conn()
    cursor = conn.execute("PRAGMA table_info(categories)")
    cols = {row[1]: row[2] for row in cursor.fetchall()}
    assert "id" in cols
    assert "name" in cols
    assert "parent_id" in cols
    conn.close()

def test_users_table():
    conn = _conn()
    cursor = conn.execute("PRAGMA table_info(users)")
    cols = {row[1]: row[2] for row in cursor.fetchall()}
    assert "id" in cols
    assert "email" in cols
    assert "name" in cols
    assert "created_at" in cols
    conn.close()

def test_users_email_unique():
    conn = _conn()
    cursor = conn.execute("PRAGMA index_list(users)")
    indexes = cursor.fetchall()
    # Check that there's a unique constraint on email
    has_unique = False
    for idx in indexes:
        idx_info = conn.execute(f"PRAGMA index_info({idx[1]})").fetchall()
        for col_info in idx_info:
            if col_info[2] == "email" and idx[2] == 1:  # unique flag
                has_unique = True
    assert has_unique, "email column should have UNIQUE constraint"
    conn.close()

def test_products_table():
    conn = _conn()
    cursor = conn.execute("PRAGMA table_info(products)")
    cols = {row[1]: row[2] for row in cursor.fetchall()}
    assert "id" in cols
    assert "name" in cols
    assert "price" in cols
    assert "category_id" in cols
    conn.close()

def test_orders_table():
    conn = _conn()
    cursor = conn.execute("PRAGMA table_info(orders)")
    cols = {row[1]: row[2] for row in cursor.fetchall()}
    assert "id" in cols
    assert "user_id" in cols
    assert "product_id" in cols
    assert "quantity" in cols
    assert "ordered_at" in cols
    conn.close()

def test_products_fk():
    conn = _conn()
    conn.execute("PRAGMA foreign_keys = ON")
    fks = conn.execute("PRAGMA foreign_key_list(products)").fetchall()
    tables = [fk[2] for fk in fks]
    assert "categories" in tables, f"products should reference categories, got {fks}"
    conn.close()

def test_orders_fks():
    conn = _conn()
    conn.execute("PRAGMA foreign_keys = ON")
    fks = conn.execute("PRAGMA foreign_key_list(orders)").fetchall()
    tables = [fk[2] for fk in fks]
    assert "users" in tables, f"orders should reference users"
    assert "products" in tables, f"orders should reference products"
    conn.close()

def test_price_check_constraint():
    """Verify CHECK(price > 0) works."""
    conn = _conn()
    conn.execute("PRAGMA foreign_keys = ON")
    # Insert a category first
    conn.execute("INSERT OR IGNORE INTO categories(id, name) VALUES (999, 'test')")
    try:
        conn.execute("INSERT INTO products(name, price, category_id) VALUES ('bad', -1, 999)")
        conn.commit()
        assert False, "Should have rejected negative price"
    except sqlite3.IntegrityError:
        pass
    conn.close()
