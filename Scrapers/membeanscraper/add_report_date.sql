-- Add report_date column to track which day the data represents
ALTER TABLE membean_students 
ADD COLUMN IF NOT EXISTS report_date timestamptz;
