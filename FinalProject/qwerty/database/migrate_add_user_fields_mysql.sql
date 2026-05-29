-- Migration script to add missing user profile fields to the users table (MySQL)
-- Run this script in your MySQL database to add the required columns

USE qwerty;

-- Add missing columns if they don't exist
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS middle_name VARCHAR(255) NULL AFTER last_name,
ADD COLUMN IF NOT EXISTS suffix VARCHAR(50) NULL AFTER middle_name,
ADD COLUMN IF NOT EXISTS phone VARCHAR(50) NULL AFTER suffix,
ADD COLUMN IF NOT EXISTS address_line1 VARCHAR(255) NULL AFTER phone,
ADD COLUMN IF NOT EXISTS address_line2 VARCHAR(255) NULL AFTER address_line1,
ADD COLUMN IF NOT EXISTS city VARCHAR(100) NULL AFTER address_line2,
ADD COLUMN IF NOT EXISTS province VARCHAR(100) NULL AFTER city,
ADD COLUMN IF NOT EXISTS region VARCHAR(100) NULL AFTER province,
ADD COLUMN IF NOT EXISTS postal_code VARCHAR(20) NULL AFTER region;

-- Note: MySQL 5.7+ supports IF NOT EXISTS for ALTER TABLE ADD COLUMN
-- If you're using an older version, you may need to check for column existence first
-- or run each ALTER TABLE statement separately and ignore errors for existing columns

