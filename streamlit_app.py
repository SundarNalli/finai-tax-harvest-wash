import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import datetime as dt
from typing import Dict, List, Optional
import json
import sys
import os

# Import from root directory modules
from db import connect, init_db, fetch_lots, fetch_recent_buys, fetch_market, insert_plan, insert_plan_items
from logic import demo_policy, WashSaleNavigator, explain_plan
from models import TaxLot, RecentBuy, MarketData
import seed

# Page configuration
st.set_page_config(
    page_title="Tax Loss Harvesting Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    .success-card {
        border-left-color: #28a745;
    }
    .warning-card {
        border-left-color: #ffc107;
    }
    .danger-card {
        border-left-color: #dc3545;
    }
    .info-card {
        border-left-color: #17a2b8;
    }
</style>
""", unsafe_allow_html=True)

def init_session_state():
    """Initialize session state variables"""
    if 'db_initialized' not in st.session_state:
        st.session_state.db_initialized = False
    if 'current_plan' not in st.session_state:
        st.session_state.current_plan = None
    if 'refresh_data' not in st.session_state:
        st.session_state.refresh_data = False

def initialize_database():
    """Initialize database and seed with demo data"""
    try:
        conn = connect()
        init_db(conn)
        seed_result = seed.seed_demo(conn)
        conn.close()
        st.session_state.db_initialized = True
        return seed_result
    except Exception as e:
        st.error(f"Error initializing database: {e}")
        return None

def get_portfolio_data():
    """Fetch current portfolio data from database"""
    try:
        conn = connect()
        
        # Fetch lots
        lots_data = fetch_lots(conn)
        lots_df = pd.DataFrame(lots_data)
        if not lots_df.empty:
            # Ensure column names are correct and handle potential missing columns
            if 'buy_date' in lots_df.columns:
                lots_df['buy_date'] = pd.to_datetime(lots_df['buy_date'])
            else:
                st.error("Database schema issue: 'buy_date' column not found in lots table")
                st.write(f"Available columns: {lots_df.columns.tolist()}")
                return None, None, None, None
                
            lots_df['total_cost'] = lots_df['shares'] * lots_df['cost_basis_per_share']
        else:
            st.warning("No tax lots found in database")
        
        # Fetch recent buys
        buys_data = fetch_recent_buys(conn)
        buys_df = pd.DataFrame(buys_data)
        if not buys_df.empty:
            if 'date' in buys_df.columns:
                buys_df['date'] = pd.to_datetime(buys_df['date'])
            else:
                st.error("Database schema issue: 'date' column not found in recent_buys table")
                return None, None, None, None
        
        # Fetch market prices
        asof, prices = fetch_market(conn)
        prices_df = pd.DataFrame(list(prices.items()), columns=['symbol', 'current_price'])
        
        conn.close()
        
        return lots_df, buys_df, prices_df, asof
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        import traceback
        st.error(f"Full traceback: {traceback.format_exc()}")
        return None, None, None, None

def calculate_portfolio_metrics(lots_df, prices_df):
    """Calculate portfolio performance metrics"""
    if lots_df.empty or prices_df.empty:
        return None
    
    # Merge lots with current prices
    portfolio = lots_df.merge(prices_df, on='symbol', how='left')
    
    # Calculate metrics
    portfolio['current_value'] = portfolio['shares'] * portfolio['current_price']
    portfolio['unrealized_pnl'] = portfolio['current_value'] - portfolio['total_cost']
    portfolio['unrealized_pnl_pct'] = (portfolio['unrealized_pnl'] / portfolio['total_cost']) * 100
    
    return portfolio

def generate_harvest_plan():
    """Generate tax loss harvesting plan"""
    try:
        conn = connect()
        
        # Fetch data
        lots_data = fetch_lots(conn)
        buys_data = fetch_recent_buys(conn)
        asof, prices = fetch_market(conn)
        
        # Convert to models
        lots = [TaxLot(
            symbol=row['symbol'],
            shares=row['shares'],
            buy_date=dt.datetime.strptime(row['buy_date'], '%Y-%m-%d').date(),
            cost_basis_per_share=row['cost_basis_per_share']
        ) for row in lots_data]
        
        buys = [RecentBuy(
            date=dt.datetime.strptime(row['date'], '%Y-%m-%d').date(),
            symbol=row['symbol'],
            shares=row['shares']
        ) for row in buys_data]
        
        market = MarketData(
            asof=dt.datetime.strptime(asof, '%Y-%m-%d').date(),
            prices=prices
        )
        
        # Get policy and generate plan
        policy = demo_policy()
        navigator = WashSaleNavigator(policy)
        plan = navigator.build_plan(lots, market, buys)
        
        conn.close()
        return plan
    except Exception as e:
        st.error(f"Error generating harvest plan: {e}")
        return None

def portfolio_overview_page():
    """Portfolio Overview Page"""
    st.markdown('<h1 class="main-header">📊 Portfolio Overview</h1>', unsafe_allow_html=True)
    
    # Initialize database if needed
    if not st.session_state.db_initialized:
        if st.button("🚀 Initialize Demo Database"):
            with st.spinner("Initializing database..."):
                seed_result = initialize_database()
                if seed_result:
                    st.success(f"Database initialized with {seed_result['lots']} lots, {seed_result['recent_buys']} recent buys, and {seed_result['market_symbols']} market symbols")
                    st.rerun()
        return
    
    # Fetch data
    lots_df, buys_df, prices_df, asof = get_portfolio_data()
    
    if lots_df is None:
        st.error("Failed to fetch portfolio data")
        return
    
    # Calculate portfolio metrics
    portfolio = calculate_portfolio_metrics(lots_df, prices_df)
    
    if portfolio is None:
        st.error("Failed to calculate portfolio metrics")
        return
    
    # Portfolio Summary Metrics
    col1, col2, col3, col4 = st.columns(4)
    
    total_cost = portfolio['total_cost'].sum()
    total_current_value = portfolio['current_value'].sum()
    total_unrealized_pnl = portfolio['unrealized_pnl'].sum()
    total_unrealized_pnl_pct = (total_unrealized_pnl / total_cost) * 100 if total_cost > 0 else 0
    
    with col1:
        st.metric("Total Cost Basis", f"${total_cost:,.2f}")
    
    with col2:
        st.metric("Current Value", f"${total_current_value:,.2f}")
    
    with col3:
        st.metric("Unrealized P&L", f"${total_unrealized_pnl:,.2f}", 
                 delta=f"{total_unrealized_pnl_pct:.2f}%")
    
    with col4:
        st.metric("Number of Positions", len(portfolio))
    
    # Portfolio Performance Chart
    st.subheader("Portfolio Performance by Position")
    
    # Create performance chart
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=("Unrealized P&L by Position", "Position Sizes"),
        vertical_spacing=0.1,
        row_heights=[0.6, 0.4]
    )
    
    # P&L chart
    colors = ['red' if x < 0 else 'green' for x in portfolio['unrealized_pnl']]
    fig.add_trace(
        go.Bar(
            x=portfolio['symbol'],
            y=portfolio['unrealized_pnl'],
            marker_color=colors,
            name="Unrealized P&L",
            text=[f"${x:,.0f}" for x in portfolio['unrealized_pnl']],
            textposition='auto'
        ),
        row=1, col=1
    )
    
    # Position sizes chart
    fig.add_trace(
        go.Bar(
            x=portfolio['symbol'],
            y=portfolio['current_value'],
            marker_color='lightblue',
            name="Current Value",
            text=[f"${x:,.0f}" for x in portfolio['current_value']],
            textposition='auto'
        ),
        row=2, col=1
    )
    
    fig.update_layout(
        height=600,
        showlegend=False,
        title_text="Portfolio Analysis"
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Detailed Portfolio Table
    st.subheader("Detailed Position Information")
    
    display_portfolio = portfolio[['symbol', 'shares', 'cost_basis_per_share', 'current_price', 
                                  'total_cost', 'current_value', 'unrealized_pnl', 'unrealized_pnl_pct']].copy()
    display_portfolio.columns = ['Symbol', 'Shares', 'Cost Basis/Share', 'Current Price', 
                                'Total Cost', 'Current Value', 'Unrealized P&L', 'P&L %']
    
    # Format currency columns
    for col in ['Cost Basis/Share', 'Current Price', 'Total Cost', 'Current Value', 'Unrealized P&L']:
        display_portfolio[col] = display_portfolio[col].apply(lambda x: f"${x:,.2f}")
    
    display_portfolio['P&L %'] = display_portfolio['P&L %'].apply(lambda x: f"{x:.2f}%")
    
    st.dataframe(display_portfolio, use_container_width=True)
    
    # Recent Buys Section
    if not buys_df.empty:
        st.subheader("Recent Purchases (Last 30 Days)")
        recent_buys_display = buys_df.copy()
        recent_buys_display.columns = ['Symbol', 'Shares', 'Date']
        recent_buys_display['Date'] = recent_buys_display['Date'].dt.strftime('%Y-%m-%d')
        st.dataframe(recent_buys_display, use_container_width=True)

def tax_harvesting_page():
    """Tax Loss Harvesting Page"""
    st.markdown('<h1 class="main-header">🌾 Tax Loss Harvesting</h1>', unsafe_allow_html=True)
    
    if not st.session_state.db_initialized:
        st.warning("Please initialize the database first from the Portfolio Overview page.")
        return
    
    # Generate harvest plan
    if st.button("🔄 Generate Harvest Plan"):
        with st.spinner("Analyzing portfolio for tax loss harvesting opportunities..."):
            plan = generate_harvest_plan()
            if plan:
                st.session_state.current_plan = plan
                st.success("Harvest plan generated successfully!")
                st.rerun()
    
    # Display current plan if available
    if st.session_state.current_plan:
        plan = st.session_state.current_plan
        
        # Plan Summary
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Harvestable Loss", f"${plan.total_harvestable_loss:,.2f}")
        
        with col2:
            st.metric("Cash Impact", f"${plan.simulated_cash_delta:,.2f}")
        
        with col3:
            st.metric("Number of Positions", len(plan.items))
        
        # Plan Details
        st.subheader("Harvest Plan Details")
        
        # Separate blocked and actionable items
        blocked_items = [item for item in plan.items if item.wash_sale_blocked]
        actionable_items = [item for item in plan.items if not item.wash_sale_blocked]
        
        # Actionable Items
        if actionable_items:
            st.success(f"✅ {len(actionable_items)} positions available for harvesting")
            
            for item in actionable_items:
                with st.expander(f"📈 {item.symbol} - Lot {item.lot_index} (${item.loss_dollars:,.2f} loss)"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**Shares to Sell:** {item.shares_to_sell:,.4f}")
                        st.write(f"**Sale Price:** ${item.sale_price:,.2f}")
                        st.write(f"**Loss Amount:** ${item.loss_dollars:,.2f}")
                        st.write(f"**Sale Date:** {item.sale_date.strftime('%Y-%m-%d')}")
                    
                    with col2:
                        st.write(f"**Replacement:** {item.replacement_symbol}")
                        st.write(f"**Replacement Shares:** {item.replacement_shares:,.4f}")
                        st.write(f"**Replacement Price:** ${item.replacement_price:,.2f}")
                        st.write(f"**Re-entry Date:** {item.reentry_date_ok_after.strftime('%Y-%m-%d')}")
        
        # Blocked Items
        if blocked_items:
            st.warning(f"⚠️ {len(blocked_items)} positions blocked by wash sale rules")
            
            for item in blocked_items:
                with st.expander(f"🚫 {item.symbol} - Lot {item.lot_index} (${item.loss_dollars:,.2f} loss)"):
                    st.write(f"**Block Reason:** {item.block_reason}")
                    st.write(f"**Shares:** {item.shares_to_sell:,.4f}")
                    st.write(f"**Potential Loss:** ${item.loss_dollars:,.2f}")
        
        # Plan Explanation
        st.subheader("Plan Explanation")
        try:
            explanation = explain_plan(plan)
            st.markdown(explanation)
        except Exception as e:
            st.error(f"Error generating explanation: {e}")
        
        # Action Buttons
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("💾 Save Plan to Database"):
                try:
                    conn = connect()
                    plan_id = insert_plan(
                        conn, 
                        plan.asof.isoformat(), 
                        plan.total_harvestable_loss, 
                        plan.simulated_cash_delta
                    )
                    
                    # Save plan items
                    items_json = [item.model_dump_json() for item in plan.items]
                    insert_plan_items(conn, plan_id, items_json)
                    conn.close()
                    
                    st.success(f"Plan saved with ID: {plan_id}")
                except Exception as e:
                    st.error(f"Error saving plan: {e}")
        
        with col2:
            if st.button("🔄 Refresh Plan"):
                st.session_state.current_plan = None
                st.rerun()

def market_data_page():
    """Market Data Page"""
    st.markdown('<h1 class="main-header">📈 Market Data</h1>', unsafe_allow_html=True)
    
    if not st.session_state.db_initialized:
        st.warning("Please initialize the database first from the Portfolio Overview page.")
        return
    
    # Fetch market data
    lots_df, buys_df, prices_df, asof = get_portfolio_data()
    
    if prices_df is None:
        st.error("Failed to fetch market data")
        return
    
    # Market Overview
    st.subheader(f"Market Prices as of {asof}")
    
    # Price distribution chart
    fig = px.histogram(
        prices_df, 
        x='current_price', 
        nbins=20,
        title="Distribution of Current Market Prices",
        labels={'current_price': 'Price ($)', 'count': 'Number of Securities'}
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Price table
    st.subheader("Current Market Prices")
    
    # Add price change simulation
    price_change = st.slider("Simulate Price Change (%)", -20, 20, 0, 1)
    
    if price_change != 0:
        prices_df['simulated_price'] = prices_df['current_price'] * (1 + price_change / 100)
        prices_df['price_change'] = prices_df['simulated_price'] - prices_df['current_price']
        prices_df['price_change_pct'] = (prices_df['price_change'] / prices_df['current_price']) * 100
        
        display_prices = prices_df[['symbol', 'current_price', 'simulated_price', 'price_change', 'price_change_pct']].copy()
        display_prices.columns = ['Symbol', 'Current Price', 'Simulated Price', 'Price Change', 'Change %']
        
        # Format currency columns
        for col in ['Current Price', 'Simulated Price', 'Price Change']:
            display_prices[col] = display_prices[col].apply(lambda x: f"${x:,.2f}")
        
        display_prices['Change %'] = display_prices['Change %'].apply(lambda x: f"{x:+.2f}%")
        
        st.dataframe(display_prices, use_container_width=True)
        
        # Impact on portfolio
        portfolio = calculate_portfolio_metrics(lots_df, prices_df)
        if portfolio is not None:
            st.subheader("Portfolio Impact of Price Change")
            
            portfolio_sim = portfolio.copy()
            portfolio_sim = portfolio_sim.merge(prices_df[['symbol', 'simulated_price']], on='symbol', how='left')
            portfolio_sim['simulated_value'] = portfolio_sim['shares'] * portfolio_sim['simulated_price']
            portfolio_sim['simulated_pnl'] = portfolio_sim['simulated_value'] - portfolio_sim['total_cost']
            portfolio_sim['pnl_change'] = portfolio_sim['simulated_pnl'] - portfolio_sim['unrealized_pnl']
            
            total_pnl_change = portfolio_sim['pnl_change'].sum()
            st.metric("Total P&L Change", f"${total_pnl_change:,.2f}")
    else:
        display_prices = prices_df.copy()
        display_prices.columns = ['Symbol', 'Current Price']
        display_prices['Current Price'] = display_prices['Current Price'].apply(lambda x: f"${x:,.2f}")
        st.dataframe(display_prices, use_container_width=True)

def settings_page():
    """Settings and Configuration Page"""
    st.markdown('<h1 class="main-header">⚙️ Settings & Configuration</h1>', unsafe_allow_html=True)
    
    st.subheader("Database Management")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🗑️ Clear All Data"):
            if st.session_state.db_initialized:
                try:
                    conn = connect()
                    from db import clear_all
                    clear_all(conn)
                    conn.close()
                    st.session_state.db_initialized = False
                    st.session_state.current_plan = None
                    st.success("All data cleared successfully")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error clearing data: {e}")
            else:
                st.warning("Database not initialized")
    
    with col2:
        if st.button("🔄 Reset to Demo Data"):
            if st.session_state.db_initialized:
                try:
                    conn = connect()
                    from db import clear_all
                    clear_all(conn)
                    seed_result = seed.seed_demo(conn)
                    conn.close()
                    st.success(f"Demo data reset successfully: {seed_result['lots']} lots, {seed_result['recent_buys']} recent buys")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error resetting data: {e}")
            else:
                st.warning("Database not initialized")
    
    st.subheader("Tax Loss Harvesting Parameters")
    
    col1, col2 = st.columns(2)
    
    with col1:
        min_loss_dollars = st.number_input("Minimum Loss Amount ($)", min_value=0.0, value=200.0, step=50.0)
        st.info("Minimum dollar amount of loss required to consider harvesting")
    
    with col2:
        min_loss_pct = st.number_input("Minimum Loss Percentage (%)", min_value=0.0, value=5.0, step=1.0) / 100
        st.info("Minimum percentage loss required to consider harvesting")
    
    st.subheader("Policy Configuration")
    
    # Display current policy
    try:
        policy = demo_policy()
        
        st.write("**Prohibited Equivalents (Wash Sale Clusters):**")
        for i, cluster in enumerate(policy.prohibited_equivalents):
            st.write(f"Cluster {i+1}: {', '.join(cluster)}")
        
        st.write("**Recommended Alternatives:**")
        for symbol, alternatives in policy.recommended_alternatives.items():
            st.write(f"{symbol} → {', '.join(alternatives)}")
    
    except Exception as e:
        st.error(f"Error loading policy: {e}")

def main():
    """Main application"""
    init_session_state()
    
    # Sidebar navigation
    st.sidebar.title("📊 Tax Loss Harvesting")
    st.sidebar.markdown("---")
    
    page = st.sidebar.selectbox(
        "Navigation",
        ["Portfolio Overview", "Tax Harvesting", "Market Data", "Settings"]
    )
    
    # Display selected page
    if page == "Portfolio Overview":
        portfolio_overview_page()
    elif page == "Tax Harvesting":
        tax_harvesting_page()
    elif page == "Market Data":
        market_data_page()
    elif page == "Settings":
        settings_page()
    
    # Footer
    st.sidebar.markdown("---")
    st.sidebar.markdown("**Tax Loss Harvesting Dashboard**")
    st.sidebar.markdown("*Demo purposes only - not tax advice*")

if __name__ == "__main__":
    main()
