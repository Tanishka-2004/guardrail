-- GuardRail PostgreSQL Initialization Script
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Initial check
SELECT 'GuardRail database initialized successfully' as status;
