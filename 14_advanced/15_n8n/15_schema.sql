-- Module 15 tables: leads (15_2), customers (15_5, 15_6) and tickets (15_3, 15_6).
-- Load with (PowerShell):
--   Get-Content 15_schema.sql | docker exec -i mysql mysql -un8n -pn8npass bizdb
-- Re-running this script resets these three tables.

DROP TABLE IF EXISTS leads;
CREATE TABLE leads (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  name        VARCHAR(100) NOT NULL,
  email       VARCHAR(150) NOT NULL,
  company     VARCHAR(150),
  budget      VARCHAR(30),
  source      VARCHAR(30),
  segment     VARCHAR(10),
  created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

DROP TABLE IF EXISTS customers;
CREATE TABLE customers (
  customer_id  VARCHAR(10) PRIMARY KEY,
  name         VARCHAR(100) NOT NULL,
  email        VARCHAR(150) NOT NULL UNIQUE,
  tier         VARCHAR(10) NOT NULL DEFAULT 'Standard'
);

INSERT INTO customers (customer_id, name, email, tier) VALUES
  ('C-001', 'Asha Patil',      'asha@example.com',  'Gold'),
  ('C-002', 'Rahul Deshmukh',  'rahul@example.com', 'Standard'),
  ('C-003', 'Meera Iyer',      'meera@example.com', 'Gold'),
  ('C-004', 'Kiran Joshi',     'kiran@example.com', 'Standard');

DROP TABLE IF EXISTS tickets;
CREATE TABLE tickets (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  ticket_id   VARCHAR(30) NOT NULL UNIQUE,
  name        VARCHAR(100),
  email       VARCHAR(150) NOT NULL,
  issue       TEXT,
  category    VARCHAR(30),
  priority    VARCHAR(10),
  sla_hours   INT,
  summary     VARCHAR(255),
  status      VARCHAR(20) NOT NULL DEFAULT 'Open',
  created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
