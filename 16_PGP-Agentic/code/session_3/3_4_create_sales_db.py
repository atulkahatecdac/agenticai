import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

conn = sqlite3.connect(os.path.join(BASE_DIR, "sales.db"))
cursor = conn.cursor()

# Drop the table if it already exists
cursor.execute("DROP TABLE IF EXISTS sales")

# Create the sales table
cursor.execute("""
CREATE TABLE sales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_name TEXT,
    sale_date TEXT,
    quantity INTEGER,
    revenue REAL
)
""")

# Sample data
sales_data = [
    ("Laptop", "2026-01-15", 5, 450000),
    ("Smartphone", "2026-02-10", 12, 360000),
    ("Tablet", "2026-03-05", 8, 200000),
    ("Monitor", "2026-03-18", 10, 180000),
    ("Keyboard", "2026-04-02", 25, 125000),
    ("Mouse", "2026-04-12", 30, 90000),
    ("Laptop", "2026-05-10", 4, 360000),
    ("Smartphone", "2026-05-25", 10, 300000),
    ("Laptop", "2026-06-15", 6, 540000),
    ("Tablet", "2026-06-28", 5, 125000),
    ("Monitor", "2026-07-08", 7, 126000),
    ("Keyboard", "2026-07-18", 20, 100000),
    ("Mouse", "2026-07-20", 40, 120000)
]

cursor.executemany("""
INSERT INTO sales (product_name, sale_date, quantity, revenue)
VALUES (?, ?, ?, ?)
""", sales_data)

conn.commit()
conn.close()

print("sales.db created successfully.")