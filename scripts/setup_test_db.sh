#!/bin/bash
#
# Setup script for PostgreSQL test database
# This script creates and initializes the test database for unit testing
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Setting up PriceSnap Test Database...${NC}"
echo ""

# Configuration (can be overridden by environment variables)
DB_NAME="${TEST_DB_NAME:-price_tracker_test}"
DB_USER="${TEST_DB_USER:-price_tracker_user}"
DB_PASS="${TEST_DB_PASS:-pass@123}"
DB_HOST="${TEST_DB_HOST:-localhost}"
DB_PORT="${TEST_DB_PORT:-5432}"

echo -e "${YELLOW}📋 Configuration:${NC}"
echo "   Database: $DB_NAME"
echo "   User: $DB_USER"
echo "   Host: $DB_HOST:$DB_PORT"
echo ""

# Check if PostgreSQL is running
echo -e "${YELLOW}🔍 Checking PostgreSQL connection...${NC}"
if ! command -v psql &> /dev/null; then
    echo -e "${RED}❌ psql command not found. Please install PostgreSQL.${NC}"
    exit 1
fi

if ! pg_isready -h "$DB_HOST" -p "$DB_PORT" &> /dev/null; then
    echo -e "${RED}❌ PostgreSQL is not running or not accessible.${NC}"
    echo "   Please start PostgreSQL and try again."
    exit 1
fi

echo -e "${GREEN}✅ PostgreSQL is running${NC}"
echo ""

# Create the database if it doesn't exist
echo -e "${YELLOW}📦 Creating database '$DB_NAME'...${NC}"
sudo -u postgres psql -c "SELECT 1 FROM pg_database WHERE datname = '$DB_NAME'" 2>/dev/null | grep -q 1

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Database '$DB_NAME' already exists${NC}"
else
    echo "   Creating database..."
    sudo -u postgres psql <<EOF
CREATE DATABASE $DB_NAME;
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;
EOF
    echo -e "${GREEN}✅ Database '$DB_NAME' created successfully${NC}"
fi
echo ""

# Create the user if it doesn't exist
echo -e "${YELLOW}👤 Setting up user '$DB_USER'...${NC}"
if sudo -u postgres psql -c "\du" | grep -q "$DB_USER"; then
    echo -e "${GREEN}✅ User '$DB_USER' already exists${NC}"
else
    echo "   Creating user..."
    sudo -u postgres psql <<EOF
CREATE USER $DB_USER WITH PASSWORD '$DB_PASS';
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;
EOF
    echo -e "${GREEN}✅ User '$DB_USER' created successfully${NC}"
fi
echo ""

# Grant schema permissions
echo -e "${YELLOW}🔐 Setting up schema permissions...${NC}"
sudo -u postgres psql -d "$DB_NAME" <<EOF
GRANT ALL ON SCHEMA public TO $DB_USER;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO $DB_USER;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO $DB_USER;
EOF
echo -e "${GREEN}✅ Permissions configured${NC}"
echo ""

# Test the connection
echo -e "${YELLOW}🔌 Testing connection...${NC}"
export PGPASSWORD="$DB_PASS"
if psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1;" &> /dev/null; then
    echo -e "${GREEN}✅ Connection successful!${NC}"
else
    echo -e "${RED}❌ Connection failed. Please check your configuration.${NC}"
    exit 1
fi
echo ""

# Create .env.test file if it doesn't exist
echo -e "${YELLOW}📄 Creating .env.test file...${NC}"
if [ ! -f ".env.test" ]; then
    cat > .env.test <<EOF
# Test Database Configuration
TEST_DATABASE_URL=postgresql://$DB_USER:$DB_PASS@$DB_HOST:$DB_PORT/$DB_NAME

# Flask Test Configuration
FLASK_ENV=testing
TESTING=1
CORS_ORIGIN=*
EOF
    echo -e "${GREEN}✅ .env.test file created${NC}"
else
    echo -e "${YELLOW}⚠️  .env.test already exists, skipping${NC}"
fi
echo ""

# Initialize the database tables
echo -e "${YELLOW}🏗️  Initializing database tables...${NC}"
python3 init_db.py
echo -e "${GREEN}✅ Database tables created${NC}"
echo ""

# Final success message
echo -e "${GREEN}🎉 Test database setup complete!${NC}"
echo ""
echo -e "${YELLOW}📝 Next steps:${NC}"
echo "   1. Update .env.test with your test credentials if needed"
echo "   2. Run tests with: pytest tests/"
echo "   3. For verbose output: pytest -v tests/"
echo ""

