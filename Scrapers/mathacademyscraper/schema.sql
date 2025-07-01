-- Update the math_academy_students table to include all fields from the JSON data
ALTER TABLE public.math_academy_students
    -- Add new columns for additional data
    ADD COLUMN IF NOT EXISTS daily_activity jsonb NULL,
    ADD COLUMN IF NOT EXISTS tasks jsonb NULL,
    ADD COLUMN IF NOT EXISTS daily_xp text NULL,
    ADD COLUMN IF NOT EXISTS weekly_xp text NULL,
    ADD COLUMN IF NOT EXISTS expected_weekly_xp text NULL,
    ADD COLUMN IF NOT EXISTS estimated_completion text NULL,
    ADD COLUMN IF NOT EXISTS student_url text NULL,
    ADD COLUMN IF NOT EXISTS percent_complete text NULL,
    ADD COLUMN IF NOT EXISTS last_activity timestamp with time zone NULL,
    ADD COLUMN IF NOT EXISTS course_name text NULL,
    ADD COLUMN IF NOT EXISTS name text NULL,
    ADD COLUMN IF NOT EXISTS student_id text NULL,
    ADD COLUMN IF NOT EXISTS created_at timestamp with time zone NULL DEFAULT now(),
    ADD COLUMN IF NOT EXISTS student_uuid uuid NULL,
    ADD COLUMN IF NOT EXISTS central_student_id uuid NULL;

-- Add constraints
DO $$ 
BEGIN
    -- Add primary key if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'math_academy_students_pkey'
    ) THEN
        ALTER TABLE public.math_academy_students
            ADD CONSTRAINT math_academy_students_pkey PRIMARY KEY (id);
    END IF;

    -- Add unique constraint if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'unique_math_academy_student_id'
    ) THEN
        ALTER TABLE public.math_academy_students
            ADD CONSTRAINT unique_math_academy_student_id UNIQUE (student_id);
    END IF;

    -- Add foreign key constraint if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'math_academy_students_central_student_id_fkey'
    ) THEN
        ALTER TABLE public.math_academy_students
            ADD CONSTRAINT math_academy_students_central_student_id_fkey 
            FOREIGN KEY (central_student_id) REFERENCES students(id);
    END IF;
END $$;

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_math_academy_student_id 
    ON public.math_academy_students USING btree (student_id) TABLESPACE pg_default;

CREATE INDEX IF NOT EXISTS idx_math_academy_student_uuid 
    ON public.math_academy_students USING btree (student_uuid) TABLESPACE pg_default;

-- Create triggers
CREATE OR REPLACE TRIGGER map_math_academy_student_trigger
    BEFORE INSERT OR UPDATE ON math_academy_students
    FOR EACH ROW
    EXECUTE FUNCTION map_student_by_name(); 