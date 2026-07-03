from sqlalchemy import create_engine

print("🔌 Testing PostgreSQL connection...")

# Simple connection string
connection_string = "postgresql://postgres:06082005vV@127.0.0.1:5432/ecommerce_analytics"

try:
    engine = create_engine(connection_string)
    with engine.connect() as conn:
        result = conn.execute("SELECT version()")
        print("✅ Connected successfully!")
        print("📊 PostgreSQL version:", result.fetchone()[0])
        print("")
        print("🚀 You can now run: python 01_generate_data.py")
except Exception as e:
    print("❌ Connection failed:", e)
    print("")
    print("💡 Please check:")
    print("   1. PostgreSQL is running")
    print("   2. pg_hba.conf uses md5 authentication")
    print("   3. Password is correct")