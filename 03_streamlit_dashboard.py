import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from sqlalchemy import create_engine
from datetime import datetime

# ============================================
# PAGE CONFIGURATION
# ============================================
st.set_page_config(
    page_title="E-commerce Analytics Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================
# DATABASE CONNECTION
# ============================================
connection_string = "postgresql://postgres:06082005vV%40@localhost:5432/ecommerce_analytics"
engine = create_engine(connection_string)

@st.cache_data(ttl=300)
def load_data():
    # Load data warehouse tables
    customers = pd.read_sql("SELECT * FROM dim_customers", engine)
    products = pd.read_sql("SELECT * FROM dim_products", engine)
    orders = pd.read_sql("SELECT * FROM fact_orders", engine)
    return customers, products, orders

customers, products, orders = load_data()

# ============================================
# SIDEBAR FILTERS
# ============================================
st.sidebar.title("🎯 Dashboard Filters")
st.sidebar.markdown("---")

# Date filter
st.sidebar.subheader("📅 Date Range")
orders['order_date'] = pd.to_datetime(orders['order_date'])
min_date = orders['order_date'].min()
max_date = orders['order_date'].max()

date_range = st.sidebar.date_input(
    "Select Date Range",
    [min_date, max_date],
    min_value=min_date,
    max_value=max_date
)

# Status filter
status_options = orders['status'].unique().tolist()
selected_status = st.sidebar.multiselect(
    "Order Status",
    status_options,
    default=status_options
)

# ============================================
# MAIN DASHBOARD
# ============================================
st.title("📊 E-commerce Analytics Dashboard")
st.markdown(f"🕒 Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
st.markdown("---")

# Filter data
mask = (orders['order_date'].dt.date >= date_range[0]) & (orders['order_date'].dt.date <= date_range[1])
filtered_orders = orders[mask]
filtered_orders = filtered_orders[filtered_orders['status'].isin(selected_status)]

# ============================================
# KPI CARDS
# ============================================
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric("💰 Total Revenue", f"${filtered_orders['total_amount'].sum():,.0f}")

with col2:
    st.metric("📦 Total Orders", f"{len(filtered_orders):,}")

with col3:
    unique_customers = filtered_orders['customer_id'].nunique()
    st.metric("👥 Customers", f"{unique_customers:,}")

with col4:
    avg_order = filtered_orders['total_amount'].mean() if len(filtered_orders) > 0 else 0
    st.metric("📊 Avg Order Value", f"${avg_order:.2f}")

with col5:
    completed = len(filtered_orders[filtered_orders['status'] == 'Completed'])
    st.metric("✅ Completed Orders", f"{completed:,}")

st.markdown("---")

# ============================================
# CHARTS ROW 1
# ============================================
col1, col2 = st.columns(2)

# Chart 1: Orders by Status
with col1:
    st.subheader("📊 Orders by Status")
    status_counts = filtered_orders['status'].value_counts()
    fig = px.pie(
        values=status_counts.values,
        names=status_counts.index,
        color_discrete_sequence=px.colors.qualitative.Set3
    )
    fig.update_traces(textposition='inside', textinfo='percent+label')
    st.plotly_chart(fig, use_container_width=True)

# Chart 2: Revenue by Payment Method
with col2:
    st.subheader("💳 Revenue by Payment Method")
    payment_revenue = filtered_orders.groupby('payment_method')['total_amount'].sum().sort_values()
    fig = px.bar(
        x=payment_revenue.values,
        y=payment_revenue.index,
        orientation='h',
        color=payment_revenue.index,
        title="Revenue by Payment Method"
    )
    fig.update_layout(showlegend=False, xaxis_title="Revenue ($)")
    st.plotly_chart(fig, use_container_width=True)

# ============================================
# CHARTS ROW 2
# ============================================
col3, col4 = st.columns(2)

# Chart 3: Daily Revenue Trend
with col3:
    st.subheader("📈 Daily Revenue Trend")
    daily_revenue = filtered_orders.groupby('order_date')['total_amount'].sum().reset_index()
    fig = px.line(
        daily_revenue,
        x='order_date',
        y='total_amount',
        title="Daily Revenue"
    )
    fig.update_layout(xaxis_title="Date", yaxis_title="Revenue ($)")
    st.plotly_chart(fig, use_container_width=True)

# Chart 4: Top Products
with col4:
    st.subheader("🏆 Top 10 Products by Revenue")
    top_products = products.nlargest(10, 'revenue')
    fig = px.bar(
        top_products,
        x='revenue',
        y='product_name',
        orientation='h',
        color='revenue',
        color_continuous_scale='Viridis',
        title="Top 10 Products"
    )
    fig.update_layout(showlegend=False, xaxis_title="Revenue ($)")
    st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# ============================================
# CUSTOMER RFM ANALYSIS
# ============================================
st.subheader("🏷️ Customer RFM Segmentation")

col5, col6 = st.columns(2)

with col5:
    # RFM Distribution
    rfm_counts = customers['rfm_segment'].value_counts()
    fig = px.pie(
        values=rfm_counts.values,
        names=rfm_counts.index,
        title="RFM Segment Distribution",
        color_discrete_sequence=px.colors.qualitative.Set2
    )
    fig.update_traces(textposition='inside', textinfo='percent+label')
    st.plotly_chart(fig, use_container_width=True)

with col6:
    # RFM Segment Metrics
    rfm_metrics = customers.groupby('rfm_segment').agg({
        'total_spent': 'mean',
        'total_orders': 'mean',
        'customer_id': 'count'
    }).rename(columns={'customer_id': 'count'})
    
    st.dataframe(
        rfm_metrics.style.background_gradient(subset=['total_spent'], cmap='Blues'),
        use_container_width=True
    )

st.markdown("---")

# ============================================
# DATA TABLE
# ============================================
st.subheader("📋 Recent Orders")
recent_orders = filtered_orders.sort_values('order_date', ascending=False).head(20)
st.dataframe(recent_orders, use_container_width=True)

# ============================================
# DOWNLOAD BUTTON
# ============================================
csv = filtered_orders.to_csv(index=False)
st.download_button(
    label="📥 Download Filtered Data (CSV)",
    data=csv,
    file_name=f"ecommerce_data_{datetime.now().strftime('%Y%m%d')}.csv",
    mime="text/csv"
)

st.markdown("---")
st.markdown("🔧 Built with Streamlit | Data Pipeline: PostgreSQL → ETL → Data Warehouse → Dashboard")