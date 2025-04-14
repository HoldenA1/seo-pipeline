-- Create DBs for strapi and another service
CREATE DATABASE strapi_db;
CREATE DATABASE aidb;

-- Create tables for services
-- CREATE TABLE IF NOT EXISTS places (
--     id TEXT PRIMARY KEY,
--     name TEXT,
--     address TEXT,
--     rating REAL,
--     reviews_count REAL,
--     editorial_summary TEXT,
--     business_site TEXT,
--     city TEXT,
--     status INT
-- );

-- CREATE TABLE IF NOT EXISTS reviews (
--     id SERIAL PRIMARY KEY,
--     place_id TEXT REFERENCES places(id) ON DELETE CASCADE,
--     author_name TEXT,
--     author_uri TEXT,
--     author_photo TEXT,
--     rating REAL,
--     publish_time TEXT,
--     review_text TEXT
-- );
