# Amazon Price Tracker

A standalone application and REST API for tracking Amazon product prices with database storage and receiving notifications when prices drop below your threshold.

## Features

- 🛒 Track multiple Amazon products
- 📧 Email notifications when prices drop
- 📱 WhatsApp notifications when prices drop
- 💾 **PostgreSQL Database** - All data stored in database (products, price history, settings)
- 🔄 **SQLite Support** - Can use SQLite for development/testing
- 📊 Price history tracking - stores all price changes over time
- 📈 Price statistics - view lowest, highest, average prices and trends
- 🖥️ Standalone GUI application
- 🌐 REST API for programmatic access
- 🔄 Automatic price checking every 2 hours

## Installation

1. Clone or download this repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Initialize the database:
```bash
python init_db.py
```

4. Configure your settings:
   - Edit `.env` file with your email credentials
   - Configure notifications via API or GUI

## Database

The application uses **PostgreSQL** database by default to store:
- Products (URL, title, threshold, current price)
- Price history (all price changes with timestamps)
- Notification settings (email, phone number)

### PostgreSQL Setup

1. **Install PostgreSQL** (if not already installed):
   ```bash
   # Ubuntu/Debian
   sudo apt-get install postgresql postgresql-contrib
   
   # macOS (using Homebrew)
   brew install postgresql
   brew services start postgresql
   
   # Windows: Download from https://www.postgresql.org/download/windows/
   ```

2. **Create Database**:
   ```bash
   # Connect to PostgreSQL
   sudo -u postgres psql
   
   # Create database and user
   CREATE DATABASE price_tracker;
   CREATE USER price_tracker_user WITH PASSWORD 'your_password';
   GRANT ALL PRIVILEGES ON DATABASE price_tracker TO price_tracker_user;
   \q
   ```

3. **Configure Database Connection** in `.env`:
   ```env
   # Option 1: Full connection string (recommended)
   DATABASE_URL=postgresql://price_tracker_user:your_password@localhost:5432/price_tracker
   
   # Option 2: Individual components
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=price_tracker
   DB_USER=price_tracker_user
   DB_PASSWORD=your_password
   ```

4. **Initialize Database Tables**:
   ```bash
   python init_db.py
   ```


### Database Schema

- **products**: Stores tracked products
- **price_history**: Stores price history entries
- **notification_settings**: Stores notification configuration

The database file (`price_tracker.db`) will be created automatically on first run if not initialized manually.


### Command-Line Tracker (Original Logic)

Run the standalone tracker script:
```bash
python run_tracker.py
```

### API Server

Start the API server:
```bash
python run_api.py
```

The API will be available at `http://localhost:5000`

## API Endpoints

See `api/API_DOCUMENTATION.md` for complete API documentation.

### Main Endpoints:
- `GET /api/health` - Health check
- `GET /api/products` - Get all products
- `POST /api/products` - Add a product
- `DELETE /api/products` - Remove a product
- `POST /api/products/check` - Check price
- `POST /api/products/update-all` - Update all prices
- `GET /api/notifications` - Get notification settings
- `PUT /api/notifications` - Update notification settings
- `GET /api/history` - Get all price history
- `GET /api/history/<url>` - Get product price history
- `GET /api/history/<url>/stats` - Get price statistics


The executables will be created in the `dist` directory.

## Configuration

### Environment Variables (.env)
```
# Email Configuration
EMAIL_ID=your@email.com
EMAIL_PASS=your_password
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587

# PostgreSQL Database Configuration
DATABASE_URL=postgresql://username:password@localhost:5432/price_tracker
# OR use individual components:
# DB_HOST=localhost
# DB_PORT=5432
# DB_NAME=price_tracker
# DB_USER=postgres
# DB_PASSWORD=postgres

## Project Structure

```
Amazon_Price_Tracker/
├── core/                 # Core functionality
│   ├── __init__.py
│   ├── price_tracker.py  # Price tracking logic with DB
│   ├── price_history.py  # Price history management
│   └── notifications.py  # Notification functions
├── database/             # Database layer
│   ├── __init__.py
│   ├── db.py            # Database connection
│   └── models.py        # SQLAlchemy models
├── api/                  # REST API
│   ├── app.py           # Flask API server
│   └── schemas.py       # Request validation schemas
├── gui/                  # GUI application
│   └── app.py           # Tkinter GUI
├── run_api.py           # API server entry point
├── run_gui.py           # GUI application entry point
├── run_tracker.py       # Standalone tracker
├── init_db.py           # Database initialization script
├── price_tracker.db     # SQLite database (only if USE_SQLITE=true)
├── config.json          # Legacy config (optional)
├── .env                 # Environment variables
└── requirements.txt     # Python dependencies
```

## Database Migration

If you have existing data in `config.json` and `price_history.json`, you can migrate to the database:

1. The application will automatically create products from config.json on first run
2. Price history will be created as you check prices

## Notes

- The application checks prices every 2 hours when tracking is active
- Products are marked as inactive (not deleted) after price alert is sent
- Price history is automatically saved to database whenever prices are checked
- Make sure your email credentials are correct for email notifications
- WhatsApp notifications require the phone number to be in international format (e.g., +919876543210)
- tkinter is part of Python's standard library - if GUI doesn't work, install: `sudo apt-get install python3-tk` (Linux)
- PostgreSQL database must be set up before first run (see Database Setup above)
- SQLite database (`price_tracker.db`) is created automatically if `USE_SQLITE=true`

## Requirements

- Python 3.7+
- See `requirements.txt` for all dependencies

## License

This project is open source and available for personal use.
