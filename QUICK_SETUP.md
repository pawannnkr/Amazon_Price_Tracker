# Quick PostgreSQL Setup Guide

## Current Error
The error `password authentication failed for user "price_tracker_user"` means the user doesn't exist or the password is incorrect.

## Solution: Create Database and User

### Option 1: Using SQL Script (Recommended)

```bash
# Run the SQL script
sudo -u postgres psql -f database/create_db.sql
```

### Option 2: Manual Setup

```bash
# Connect to PostgreSQL
sudo -u postgres psql

# Then run these commands:
CREATE DATABASE price_tracker;
CREATE USER price_tracker_user WITH PASSWORD 'pass@123';
GRANT ALL PRIVILEGES ON DATABASE price_tracker TO price_tracker_user;

# Connect to the database
\c price_tracker

# Grant schema privileges
GRANT ALL ON SCHEMA public TO price_tracker_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO price_tracker_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO price_tracker_user;

# Exit
\q
```

### Option 3: One-liner Command

```bash
sudo -u postgres psql <<EOF
CREATE DATABASE price_tracker;
CREATE USER price_tracker_user WITH PASSWORD 'pass@123';
GRANT ALL PRIVILEGES ON DATABASE price_tracker TO price_tracker_user;
\c price_tracker
GRANT ALL ON SCHEMA public TO price_tracker_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO price_tracker_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO price_tracker_user;
EOF
```

## Verify Setup

After creating the database and user, test the connection:

```bash
python database/test_connection.py
```

## Initialize Tables

Once connection is successful:

```bash
python init_db.py
```

## If You Want to Change the Password

If you want to use a different password:

1. Update `.env` file with new password
2. Update PostgreSQL user password:
```bash
sudo -u postgres psql
ALTER USER price_tracker_user WITH PASSWORD 'your_new_password';
\q
```

## Troubleshooting

### PostgreSQL not running
```bash
sudo systemctl start postgresql
sudo systemctl status postgresql
```

### User already exists
If user exists but password is wrong:
```bash
sudo -u postgres psql
ALTER USER price_tracker_user WITH PASSWORD 'pass@123';
\q
```

### Database already exists
If database exists, you can drop and recreate:
```bash
sudo -u postgres psql
DROP DATABASE IF EXISTS price_tracker;
CREATE DATABASE price_tracker;
-- Then continue with user creation
```
