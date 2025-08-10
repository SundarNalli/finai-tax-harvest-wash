# Tax Loss Harvesting Dashboard

A comprehensive application for managing tax loss harvesting strategies with wash sale detection and portfolio optimization.

## Features

- **Portfolio Management**: Track tax lots, cost basis, and unrealized gains/losses
- **Tax Loss Harvesting**: Automatically identify harvesting opportunities while avoiding wash sales
- **Wash Sale Detection**: Built-in logic to prevent wash sale violations
- **Replacement Strategies**: Smart suggestions for tax-efficient replacements
- **Interactive Dashboard**: Beautiful Streamlit UI with charts and analytics
- **Demo Data**: Pre-loaded sample portfolio for testing and demonstration

## Project Structure

This project uses a **flat directory structure** where all Python modules are located in the root directory. This simplifies imports and makes the application easier to run and deploy. The main components are:

- **Core Modules**: `main.py`, `models.py`, `logic.py`, `db.py`, `seed.py`
- **UI**: `streamlit_app.py` for the interactive dashboard
- **Testing**: `test_wash_sale.py` and `test_imports.py` for validation
- **Configuration**: `requirements.txt`, `pyproject.toml`, and `uv.lock` for dependencies

## Quick Start

### Option 1: Run with Streamlit (Recommended)

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Launch the dashboard**:
   ```bash
   streamlit run streamlit_app.py
   ```

3. **Open your browser** and navigate to `http://localhost:8501`

### Option 2: Run with FastAPI

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Start the API server**:
   ```bash
   uvicorn main:app --reload
   ```

3. **Access the API** at `http://localhost:8000`

## Streamlit Dashboard

The Streamlit UI provides four main pages:

### 📊 Portfolio Overview
- **Portfolio Summary**: Total cost basis, current value, and P&L metrics
- **Performance Charts**: Interactive charts showing position performance
- **Position Details**: Comprehensive table of all tax lots
- **Recent Purchases**: Track recent buys that may affect wash sale rules

### 🌾 Tax Loss Harvesting
- **Harvest Plan Generation**: One-click generation of tax loss harvesting strategies
- **Wash Sale Analysis**: Clear identification of blocked vs. actionable positions
- **Replacement Recommendations**: Smart suggestions for tax-efficient alternatives
- **Plan Explanation**: AI-powered explanation of the harvesting strategy

### 📈 Market Data
- **Current Prices**: Real-time market data for all tracked securities
- **Price Distribution**: Histogram analysis of current market prices
- **Price Simulation**: Interactive sliders to simulate market scenarios
- **Portfolio Impact**: Calculate how price changes affect your portfolio

### ⚙️ Settings & Configuration
- **Database Management**: Clear data, reset to demo, or initialize fresh
- **Harvesting Parameters**: Adjust minimum loss thresholds and percentages
- **Policy Configuration**: View wash sale clusters and replacement rules

## Demo Data

The application comes with pre-loaded demo data including:

- **Sample Portfolio**: 6 positions with mixed P&L scenarios
- **Market Prices**: Current prices for 20+ securities
- **Wash Sale Rules**: Pre-configured clusters and alternatives
- **Recent Purchases**: Sample data to demonstrate wash sale detection

## Key Concepts

### Tax Loss Harvesting
Tax loss harvesting is a strategy to sell securities at a loss to offset capital gains taxes, then immediately purchase a similar (but not substantially identical) security to maintain market exposure.

### Wash Sale Rules
The IRS prohibits claiming a loss on a security if you purchase a "substantially identical" security within 30 days before or after the sale. This application helps you avoid these violations.

### Replacement Securities
When harvesting losses, you need to purchase replacement securities that:
- Are not substantially identical to the sold security
- Maintain similar market exposure
- Don't trigger additional wash sale rules

## Technical Architecture

- **Backend**: FastAPI with SQLite database
- **Frontend**: Streamlit with Plotly charts
- **Models**: Pydantic for data validation
- **Logic**: Custom wash sale detection algorithms
- **Database**: SQLite with WAL mode for performance
- **Structure**: Flat directory structure with all modules in the root directory

## File Structure

```
finai-tax-harvest-wash/
├── main.py                 # FastAPI application
├── models.py               # Pydantic data models
├── logic.py                # Business logic and algorithms
├── db.py                   # Database operations
├── seed.py                 # Demo data seeding
├── streamlit_app.py        # Streamlit dashboard
├── run_streamlit.py        # Streamlit launcher
├── test_wash_sale.py       # Unit tests
├── test_imports.py         # Import testing utility
├── requirements.txt        # Python dependencies
├── pyproject.toml         # Project configuration
├── uv.lock                # Dependency lock file
├── tlh.sqlite             # SQLite database
├── .python-version        # Python version specification
└── README.md              # This file
```

## Configuration

### Customizing Harvesting Parameters

You can adjust the minimum thresholds for tax loss harvesting:

- **Minimum Loss Amount**: Dollar amount threshold (default: $200)
- **Minimum Loss Percentage**: Percentage threshold (default: 5%)

### Adding Custom Securities

To add your own securities:

1. Use the database functions in `db.py`
2. Follow the data models in `models.py`
3. Update the policy configuration in `logic.py`

## API Endpoints

The FastAPI backend provides these endpoints:

- `GET /`: API documentation
- `GET /portfolio`: Current portfolio data
- `POST /harvest-plan`: Generate tax loss harvesting plan
- `GET /market-data`: Current market prices
- `POST /execute-plan`: Execute a harvesting plan

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## Disclaimer

**This application is for educational and demonstration purposes only. It is not intended to provide tax advice. Always consult with a qualified tax professional before implementing any tax strategies.**

## License

This project is open source and available under the MIT License.
