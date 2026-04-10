-- Create the database for the Notes App
CREATE DATABASE IF NOT EXISTS notes_db;

-- Use the database
USE notes_db;

-- Note: The tables will be created automatically by SQLAlchemy via db.create_all()
-- in the init_db.py script or when the app starts.
-- This script ensures the database container exists in MySQL/XAMPP.
