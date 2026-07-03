import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
from faker import Faker
import os
from sqlalchemy import create_engine, text
import psycopg2

# Initialize Faker for realistic data
fake = Faker()
Faker.seed(42)
np.random.seed(42)

print("=" * 60)
print("🚀 E-COMMERCE DATA GENERATOR")
print("=" * 60)

# ============================================
# CONFIGURATION
# ============================================
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'ecommerce_analytics',
    'user': 'postgres',
    'password': '06082005vV@'
}

# Data sizes (FAST VERSION)
NUM_CUSTOMERS = 5000
NUM_PRODUCTS = 10000
NUM_ORDERS = 5000

print(f"📊 Generating FAST version:")
print(f"   - {NUM_CUSTOMERS:,} customers")
print(f"   - {NUM_PRODUCTS:,} products")
print(f"   - {NUM_ORDERS:,} orders")
print("")

# ============================================
# PART 1: Generate Customers
# ============================================
print("🔄 Generating customers...")
def generate_customers(n=5000):
    customers = []
    for i in range(n):
        customers.append({
            'customer_id': i + 1,
            'first_name': fake.first_name(),
            'last_name': fake.last_name(),
            'email': fake.email(),
            'phone': fake.phone_number()[:15],
            'city': fake.city(),
            'state': fake.state_abbr(),
            'zip_code': fake.zipcode(),
            'signup_date': fake.date_between(start_date='-3y', end_date='today'),
            'customer_segment': np.random.choice(['Premium', 'Gold', 'Silver', 'Bronze'], p=[0.1, 0.2, 0.3, 0.4]),
            'is_active': np.random.choice([True, False], p=[0.8, 0.2])
        })
    return pd.DataFrame(customers)

customers_df = generate_customers(NUM_CUSTOMERS)
print(f"   ✅ Generated {len(customers_df):,} customers")

# ============================================
# PART 2: Generate Products
# ============================================
print("🔄 Generating products...")
def generate_products(n=10000):
    categories = ['Electronics', 'Clothing', 'Home & Kitchen', 'Books', 'Sports', 
                  'Beauty', 'Toys', 'Automotive', 'Health', 'Garden']
    sub_categories = ['Premium', 'Standard', 'Budget', 'Luxury', 'Eco-friendly']
    
    products = []
    for i in range(n):
        price = np.random.uniform(5, 5000)
        products.append({
            'product_id': i + 1,
            'product_name': fake.catch_phrase(),
            'category': np.random.choice(categories),
            'sub_category': np.random.choice(sub_categories),
            'price': round(price, 2),
            'cost': round(price * np.random.uniform(0.4, 0.8), 2),
            'stock_quantity': np.random.randint(0, 1000),
            'supplier': fake.company(),
            'rating': round(np.random.uniform(1, 5), 1),
            'review_count': np.random.randint(0, 500),
            'created_at': fake.date_between(start_date='-2y', end_date='today')
        })
    return pd.DataFrame(products)

products_df = generate_products(NUM_PRODUCTS)
print(f"   ✅ Generated {len(products_df):,} products")

# ============================================
# PART 3: Generate Orders
# ============================================
print("🔄 Generating orders...")
def generate_orders(n=5000, customers_df=None):
    orders = []
    start_date = datetime.now() - timedelta(days=365)
    
    for i in range(n):
        customer = customers_df.sample(1).iloc[0]
        order_date = fake.date_between(start_date=start_date, end_date='today')
        
        orders.append({
            'order_id': 100000 + i,
            'customer_id': customer['customer_id'],
            'order_date': order_date,
            'status': np.random.choice(['Completed', 'Shipped', 'Processing', 'Cancelled', 'Refunded'],
                                       p=[0.6, 0.2, 0.1, 0.05, 0.05]),
            'shipping_address': fake.address().replace('\n', ', '),
            'payment_method': np.random.choice(['Credit Card', 'Debit Card', 'UPI', 'Net Banking', 'COD'],
                                               p=[0.3, 0.25, 0.2, 0.15, 0.1]),
            'delivery_date': None,
            'is_gift': np.random.choice([True, False], p=[0.05, 0.95])
        })
        
    return pd.DataFrame(orders)

orders_df = generate_orders(NUM_ORDERS, customers_df)

# Update delivery dates for completed orders
orders_df.loc[orders_df['status'] == 'Completed', 'delivery_date'] = \
    orders_df.loc[orders_df['status'] == 'Completed', 'order_date'] + pd.Timedelta(days=5)

print(f"   ✅ Generated {len(orders_df):,} orders")

# ============================================
# PART 4: Generate Order Items
# ============================================
print("🔄 Generating order items...")
def generate_order_items(orders_df, products_df):
    order_items = []
    
    for _, order in orders_df.iterrows():
        num_items = np.random.randint(1, 6)
        order_products = products_df.sample(num_items)
        
        for _, product in order_products.iterrows():
            quantity = np.random.randint(1, 4)
            price = product['price']
            discount = np.random.uniform(0, 0.3)
            
            order_items.append({
                'order_item_id': len(order_items) + 1,
                'order_id': order['order_id'],
                'product_id': product['product_id'],
                'quantity': quantity,
                'unit_price': round(price, 2),
                'discount_percent': round(discount, 2),
                'total_amount': round(quantity * price * (1 - discount), 2)
            })
    
    return pd.DataFrame(order_items)

order_items_df = generate_order_items(orders_df, products_df)
print(f"   ✅ Generated {len(order_items_df):,} order items")

# ============================================
# PART 5: Create Data Directory and Save CSV
# ============================================
print("💾 Saving CSV backups...")

if not os.path.exists('data'):
    os.makedirs('data')

customers_df.to_csv('data/customers.csv', index=False)
products_df.to_csv('data/products.csv', index=False)
orders_df.to_csv('data/orders.csv', index=False)
order_items_df.to_csv('data/order_items.csv', index=False)
print("   ✅ CSV files saved to /data folder")

# ============================================
# PART 6: Load to PostgreSQL - COMPLETELY FIXED
# ============================================
print("📤 Loading to PostgreSQL...")

def load_to_postgres(df, table_name):
    try:
        # URL-encode the @ symbol in password
        connection_string = f"postgresql://postgres:06082005vV%40@localhost:5432/ecommerce_analytics"
        engine = create_engine(connection_string)
        
        # Test connection using text() for SQLAlchemy 2.0
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print(f"   ✅ Connected to PostgreSQL")
        
        df.to_sql(table_name, engine, if_exists='replace', index=False)
        print(f"   ✅ Loaded {len(df):,} rows to {table_name}")
    except Exception as e:
        print(f"   ❌ Error loading to {table_name}: {e}")

# Load all tables
load_to_postgres(customers_df, 'customers')
load_to_postgres(products_df, 'products')
load_to_postgres(orders_df, 'orders')
load_to_postgres(order_items_df, 'order_items')

# ============================================
# SUMMARY
# ============================================
print("")
print("=" * 60)
print("✅ DATA GENERATION COMPLETE!")
print("=" * 60)
print(f"📊 Final Data Summary:")
print(f"   - Customers:   {len(customers_df):,}")
print(f"   - Products:    {len(products_df):,}")
print(f"   - Orders:      {len(orders_df):,}")
print(f"   - Order Items: {len(order_items_df):,}")
print("")
print("🗄️ Data loaded to PostgreSQL database: ecommerce_analytics")
print("📁 CSV backups saved to: /data folder")
print("=" * 60)