-- Create the database and user
CREATE DATABASE teacherfy_db;
CREATE USER teacherfy_user WITH PASSWORD '132392';
GRANT ALL PRIVILEGES ON DATABASE teacherfy_db TO teacherfy_user;