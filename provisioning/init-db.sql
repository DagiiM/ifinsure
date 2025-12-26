-- PostgreSQL Initialization Script for iFinsure
-- This script runs when the database container is first created

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Set timezone
SET timezone = 'Africa/Nairobi';

-- Grant permissions (if not already granted)
GRANT ALL PRIVILEGES ON DATABASE ifinsure_db TO ifinsure;
