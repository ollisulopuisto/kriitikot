import sqlite3
import os

dbs = ['reviews.db', 'kriitikot.db', 'narmo_test.db']

def search_db(db_name, term):
    if not os.path.exists(db_name):
        return
    print(f"Searching {db_name} for '{term}'...")
    try:
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        for table in tables:
            table_name = table[0]
            # print(f"  Checking table {table_name}")
            
            # Get all columns
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = [info[1] for info in cursor.fetchall()]
            
            # Search each column
            for col in columns:
                try:
                    query = f"SELECT * FROM {table_name} WHERE {col} LIKE ?"
                    cursor.execute(query, (f'%{term}%',))
                    results = cursor.fetchall()
                    if results:
                        print(f"  FOUND in {table_name}.{col}:")
                        for row in results[:5]:
                            print(f"    {row}")
                except Exception as e:
                    pass
        conn.close()
    except Exception as e:
        print(f"Error reading {db_name}: {e}")

print("Starting search...")
search_db('reviews.db', 'Fantasia')
search_db('reviews.db', 'valitse')
search_db('kriitikot.db', 'Fantasia')
search_db('kriitikot.db', 'valitse')
