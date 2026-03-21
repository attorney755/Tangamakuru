import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()

try:
    # Get database URL from .env
    db_url = os.getenv('DATABASE_URL')
    print(f"Attempting to connect to: {db_url.split('@')[-1]}")
    
    # Try to connect
    conn = psycopg2.connect(db_url)
    print("✅ SUCCESS: Connected to PostgreSQL!")
    
    # Check database name
    cursor = conn.cursor()
    cursor.execute("SELECT current_database();")
    db_name = cursor.fetchone()[0]
    print(f"📊 Database name: {db_name}")
    
    # Check tables (should be empty for now)
    cursor.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
    """)
    tables = cursor.fetchall()
    print(f"📋 Tables in database: {len(tables)}")
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"❌ FAILED: {e}")
    print("\nTroubleshooting steps:")
    print("1. Check if PostgreSQL is running: sudo systemctl status postgresql")
    print("2. Check .env file has correct DATABASE_URL")
    print("3. Check password in CREATE USER command")