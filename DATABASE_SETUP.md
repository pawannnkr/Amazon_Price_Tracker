# Database Setup Guide

## PostgreSQL Setup (Recommended for Production)

### 1. Install PostgreSQL

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

**macOS:**
```bash
brew install postgresql
brew services start postgresql
```

**Windows:**
Download and install from: https://www.postgresql.org/download/windows/

### 2. Create Database and User

#### Option A: Using the Setup Script (Linux/macOS)
```bash
./database/setup_postgres.sh
```

#### Option B: Manual Setup
```bash
# Connect to PostgreSQL as postgres user
sudo -u postgres psql

# In PostgreSQL prompt:
CREATE DATABASE price_tracker;
CREATE USER price_tracker_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE price_tracker TO price_tracker_user;

# Connect to the new database
\c price_tracker

# Grant schema privileges
GRANT ALL ON SCHEMA public TO price_tracker_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO price_tracker_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO price_tracker_user;

# Exit
\q
```

### 3. Configure Connection

Edit `.env` file:

**Option 1: Full Connection String (Recommended)**
```env
DATABASE_URL=postgresql://price_tracker_user:your_secure_password@localhost:5432/DB_name
```

**Option 2: Individual Components**
```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=price_tracker
DB_USER=price_tracker_user
DB_PASSWORD=your_secure_password
```

### 4. Initialize Database Tables

```bash
python init_db.py
```

You should see:
```
🗄️  Initializing database...
✅ Database initialized successfully!
```

## SQLite Setup (Development/Testing)

For development or testing, you can use SQLite instead:

1. Set in `.env`:
```env
USE_SQLITE=true
```

2. Initialize database:
```bash
python init_db.py
```

This will create a local `price_tracker.db` file.

## Connection String Formats

### PostgreSQL
```
postgresql://username:password@host:port/database
```

## Troubleshooting

### Connection Refused
- Check if PostgreSQL is running: `sudo systemctl status postgresql`
- Verify host and port in `.env`
- Check firewall settings

### Authentication Failed
- Verify username and password
- Check `pg_hba.conf` for authentication settings
- Ensure user has proper permissions

### Database Does Not Exist
- Create database: `CREATE DATABASE price_tracker;`
- Verify database name in `.env`

### Permission Denied
- Grant privileges: `GRANT ALL PRIVILEGES ON DATABASE price_tracker TO username;`
- Check user permissions

## Testing Connection

You can test your database connection:

```python
from database.db import engine
from sqlalchemy import text

# Test connection
with engine.connect() as conn:
    result = conn.execute(text("SELECT version()"))
    print(result.fetchone())
```

## Migration from SQLite to PostgreSQL

If you have existing data in SQLite and want to migrate:

1. Export data from SQLite (if needed)
2. Set up PostgreSQL connection in `.env`
3. Run `python init_db.py` to create tables
4. Import data (if you have export scripts)

## Production Recommendations

1. **Use Connection Pooling**: Already configured in `database/db.py`
2. **Enable SSL**: Add `?sslmode=require` to connection string
3. **Backup Regularly**: Set up automated PostgreSQL backups
4. **Monitor Performance**: Use PostgreSQL monitoring tools
5. **Secure Credentials**: Never commit `.env` file to version control
