-- SQL to add missing columns to membean_students table
ALTER TABLE membean_students 
ADD COLUMN IF NOT EXISTS created_at_central timestamptz,
ADD COLUMN IF NOT EXISTS updated_at_central timestamptz,
ADD COLUMN IF NOT EXISTS report_date timestamptz;
