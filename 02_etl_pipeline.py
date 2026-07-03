import pandas as pd
import numpy as np
from datetime import datetime
from sqlalchemy import create_engine, text

print("=" * 60)
print("🔄 ETL PIPELINE - E-COMMERCE ANALYTICS")
print("=" * 60)

# ============================================
# CONNECTION
# ============================================
connection_string = "postgresql://postgres:06082005vV%40@localhost:5432/ecommerce_analytics"
engine = create_engine(connection_string)

print("📤 Extracting data from PostgreSQL...")

# ============================================
# EXTRACT
# ============================================
customers = pd.read_sql("SELECT * FROM customers", engine)
products = pd.read_sql("SELECT * FROM products", engine)
orders = pd.read_sql("SELECT * FROM orders", engine)
order_items = pd.read_sql("SELECT * FROM order_items", engine)

print(f"   ✅ Customers: {len(customers):,}")
print(f"   ✅ Products: {len(products):,}")
print(f"   ✅ Orders: {len(orders):,}")
print(f"   ✅ Order Items: {len(order_items):,}")

# ============================================
# TRANSFORM
# ============================================
print("\n🔄 Transforming data...")

# 1. Calculate order totals
order_totals = order_items.groupby('order_id').agg({
    'total_amount': 'sum',
    'quantity': 'sum',
    'product_id': 'count'
}).rename(columns={'product_id': 'item_count'})

orders = orders.merge(order_totals, on='order_id', how='left')

# 2. Customer metrics
customer_metrics = orders.groupby('customer_id').agg({
    'order_id': 'count',
    'total_amount': 'sum',
    'order_date': ['min', 'max']
})

customer_metrics.columns = ['total_orders', 'total_spent', 'first_order', 'last_order']
customers = customers.merge(customer_metrics, on='customer_id', how='left')

# 3. Calculate customer lifetime
today = datetime.now()
customers['first_order'] = pd.to_datetime(customers['first_order'])
customers['last_order'] = pd.to_datetime(customers['last_order'])
customers['days_since_last_order'] = (today - customers['last_order']).dt.days.fillna(999)
customers['customer_age_days'] = (today - customers['first_order']).dt.days.fillna(0)

# 4. Fill NaN values BEFORE RFM
customers['total_orders'] = customers['total_orders'].fillna(0)
customers['total_spent'] = customers['total_spent'].fillna(0)
customers['days_since_last_order'] = customers['days_since_last_order'].fillna(999)

# 5. RFM Segmentation - FIXED VERSION
def calculate_rfm(df):
    # Create a copy to avoid SettingWithCopyWarning
    df_copy = df.copy()
    
    # Recency: days since last order (lower is better)
    # Use rank to handle duplicate values
    df_copy['r_score'] = pd.qcut(
        df_copy['days_since_last_order'].rank(method='first'), 
        4, 
        labels=[4, 3, 2, 1]
    )
    
    # Frequency: total orders (higher is better)
    df_copy['f_score'] = pd.qcut(
        df_copy['total_orders'].rank(method='first'), 
        4, 
        labels=[1, 2, 3, 4]
    )
    
    # Monetary: total spent (higher is better)
    df_copy['m_score'] = pd.qcut(
        df_copy['total_spent'].rank(method='first'), 
        4, 
        labels=[1, 2, 3, 4]
    )
    
    # Convert to int (handling NaN values)
    df_copy['r_score'] = df_copy['r_score'].fillna(1).astype(int)
    df_copy['f_score'] = df_copy['f_score'].fillna(1).astype(int)
    df_copy['m_score'] = df_copy['m_score'].fillna(1).astype(int)
    
    df_copy['rfm_score'] = df_copy['r_score'] * 100 + df_copy['f_score'] * 10 + df_copy['m_score']
    
    def rfm_segment(score):
        if score >= 400:
            return '🏆 Champions'
        elif score >= 300:
            return '⭐ Loyal'
        elif score >= 200:
            return '🔄 Potential Loyalists'
        elif score >= 100:
            return '⚠️ At Risk'
        else:
            return '📉 Lost'
    
    df_copy['rfm_segment'] = df_copy['rfm_score'].apply(rfm_segment)
    return df_copy

customers = calculate_rfm(customers)

# 6. Product profitability
product_profit = order_items.groupby('product_id').agg({
    'total_amount': 'sum',
    'quantity': 'sum'
}).rename(columns={'total_amount': 'revenue', 'quantity': 'units_sold'})

products = products.merge(product_profit, on='product_id', how='left')
products['revenue'] = products['revenue'].fillna(0)
products['units_sold'] = products['units_sold'].fillna(0)
products['profit'] = products['revenue'] - (products['units_sold'] * products['cost'])
products['profit_margin'] = (products['profit'] / products['revenue'] * 100).fillna(0)

print("   ✅ Transformations complete!")

# ============================================
# LOAD - Create Data Warehouse Tables
# ============================================
print("\n📥 Loading to Data Warehouse...")

# Dimension tables
dim_customers = customers[['customer_id', 'first_name', 'last_name', 'email', 'city', 'state',
                          'customer_segment', 'total_orders', 'total_spent', 
                          'rfm_segment', 'days_since_last_order']].copy()

dim_products = products[['product_id', 'product_name', 'category', 'sub_category',
                         'price', 'cost', 'rating', 'review_count', 
                         'revenue', 'units_sold', 'profit', 'profit_margin']].copy()

# Fact table
fact_orders = orders[['order_id', 'customer_id', 'order_date', 'status', 
                      'payment_method', 'total_amount', 'item_count']].copy()

# Handle NaN values before loading
dim_customers = dim_customers.fillna(0)
dim_products = dim_products.fillna(0)
fact_orders = fact_orders.fillna(0)

# Load to PostgreSQL
dim_customers.to_sql('dim_customers', engine, if_exists='replace', index=False)
dim_products.to_sql('dim_products', engine, if_exists='replace', index=False)
fact_orders.to_sql('fact_orders', engine, if_exists='replace', index=False)

print(f"   ✅ dim_customers: {len(dim_customers):,} rows")
print(f"   ✅ dim_products: {len(dim_products):,} rows")
print(f"   ✅ fact_orders: {len(fact_orders):,} rows")

# ============================================
# ANALYTICS
# ============================================
print("\n📊 Generating Analytics...")

# KPI Summary
kpi = pd.read_sql("""
    SELECT 
        COUNT(DISTINCT customer_id) as total_customers,
        COUNT(DISTINCT order_id) as total_orders,
        COALESCE(SUM(total_amount), 0) as total_revenue,
        COALESCE(AVG(total_amount), 0) as avg_order_value,
        COUNT(DISTINCT CASE WHEN status = 'Completed' THEN order_id END) as completed_orders
    FROM fact_orders
""", engine)

print(f"   💰 Total Revenue: ${kpi['total_revenue'].iloc[0]:,.2f}")
print(f"   📦 Total Orders: {kpi['total_orders'].iloc[0]:,}")
print(f"   👥 Total Customers: {kpi['total_customers'].iloc[0]:,}")
print(f"   📊 Avg Order Value: ${kpi['avg_order_value'].iloc[0]:.2f}")

# RFM Distribution
rfm_counts = customers['rfm_segment'].value_counts()
print("\n   🏷️ RFM Segment Distribution:")
for segment, count in rfm_counts.items():
    print(f"      {segment}: {count:,} ({count/len(customers)*100:.1f}%)")

# ============================================
# SUMMARY
# ============================================
print("\n" + "=" * 60)
print("✅ ETL PIPELINE COMPLETE!")
print("=" * 60)
print("\n📊 Data Warehouse Tables Created:")
print("   - dim_customers (customer attributes + RFM)")
print("   - dim_products (product details + profitability)")
print("   - fact_orders (order transactions)")
print("\n💡 Next step: Run the Streamlit dashboard!")
print("   Command: streamlit run 03_streamlit_dashboard.py")
print("=" * 60)