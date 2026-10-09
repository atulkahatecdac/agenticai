-- BrightPath Solutions IT Helpdesk - sample data.
-- This file IS the data: helpdesk.db was built from it once with
--     sqlite3 data/helpdesk.db < data/seed.sql
-- Run that same command again (after deleting helpdesk.db) to reset the demo.

CREATE TABLE employees (
    employee_id     TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    email           TEXT NOT NULL,
    department      TEXT NOT NULL,
    role            TEXT NOT NULL,
    employment_type TEXT NOT NULL,          -- Employee | Contractor
    manager_id      TEXT,
    location        TEXT NOT NULL,
    account_status  TEXT NOT NULL           -- active | locked
);

CREATE TABLE assets (
    asset_id      TEXT PRIMARY KEY,
    employee_id   TEXT NOT NULL,
    type          TEXT NOT NULL,            -- Laptop | Phone
    model         TEXT NOT NULL,
    os            TEXT NOT NULL,
    purchase_date TEXT NOT NULL
);

CREATE TABLE entitlements (
    employee_id TEXT NOT NULL,
    system      TEXT NOT NULL,
    granted_on  TEXT NOT NULL,
    PRIMARY KEY (employee_id, system)
);

CREATE TABLE service_status (
    service    TEXT PRIMARY KEY,
    status     TEXT NOT NULL,               -- operational | degraded | down
    message    TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE tickets (
    ticket_id      INTEGER PRIMARY KEY,
    employee_id    TEXT NOT NULL,
    category       TEXT NOT NULL,
    priority       TEXT NOT NULL,           -- P1 | P2 | P3 | P4
    summary        TEXT NOT NULL,
    status         TEXT NOT NULL,           -- open | in_progress | resolved
    assigned_group TEXT NOT NULL,
    created_at     TEXT NOT NULL
);

CREATE TABLE access_requests (
    request_id  INTEGER PRIMARY KEY,
    employee_id TEXT NOT NULL,
    system      TEXT NOT NULL,
    tier        TEXT NOT NULL,              -- restricted | highly_restricted
    reason      TEXT NOT NULL,
    approvers   TEXT NOT NULL,              -- who must approve, e.g. "E1005 (manager)"
    status      TEXT NOT NULL,              -- pending | approved | rejected
    decided_by  TEXT,
    created_at  TEXT NOT NULL
);

-- ---------------------------------------------------------------- employees
INSERT INTO employees VALUES
('E1001', 'Priya Sharma',    'priya.sharma@brightpath.example',    'Engineering', 'Software Engineer',   'Employee',   'E1005', 'Pune',      'active'),
('E1002', 'Rahul Mehta',     'rahul.mehta@brightpath.example',     'Finance',     'Financial Analyst',   'Employee',   'E1006', 'Mumbai',    'locked'),
('E1003', 'Anita Desai',     'anita.desai@brightpath.example',     'Sales',       'Account Executive',   'Employee',   'E1007', 'Bengaluru', 'active'),
('E1004', 'Karan Singh',     'karan.singh@brightpath.example',     'Engineering', 'Contract Developer',  'Contractor', 'E1005', 'Pune',      'active'),
('E1005', 'Meera Iyer',      'meera.iyer@brightpath.example',      'Engineering', 'Engineering Manager', 'Employee',   NULL,    'Pune',      'active'),
('E1006', 'Vikram Rao',      'vikram.rao@brightpath.example',      'Finance',     'Finance Manager',     'Employee',   NULL,    'Mumbai',    'active'),
('E1007', 'Sanjay Kulkarni', 'sanjay.kulkarni@brightpath.example', 'Sales',       'Sales Manager',       'Employee',   NULL,    'Bengaluru', 'active');

-- ---------------------------------------------------------------- assets
INSERT INTO assets VALUES
('LT-2201', 'E1001', 'Laptop', 'Dell Latitude 7440',  'Windows 11', '2024-03-12'),
('LT-1874', 'E1002', 'Laptop', 'Lenovo ThinkPad T14', 'Windows 11', '2021-08-02'),
('LT-2310', 'E1003', 'Laptop', 'MacBook Air M2',      'macOS 15',   '2024-01-20'),
('PH-0412', 'E1003', 'Phone',  'iPhone 15',           'iOS 19',     '2024-01-20'),
('LT-2455', 'E1004', 'Laptop', 'Dell Latitude 7440',  'Windows 11', '2026-02-05'),
('LT-1702', 'E1005', 'Laptop', 'Dell Latitude 7440',  'Windows 11', '2022-11-15'),
('LT-1655', 'E1006', 'Laptop', 'Lenovo ThinkPad T14', 'Windows 11', '2022-06-30'),
('LT-1990', 'E1007', 'Laptop', 'MacBook Air M2',      'macOS 15',   '2023-05-08');

-- ---------------------------------------------------------------- entitlements
INSERT INTO entitlements VALUES
('E1001', 'Slack', '2024-03-12'), ('E1001', 'Zoom', '2024-03-12'), ('E1001', 'Microsoft 365', '2024-03-12'),
('E1001', 'GitHub', '2024-03-15'), ('E1001', 'Jira', '2024-03-15'),
('E1002', 'Slack', '2021-08-02'), ('E1002', 'Zoom', '2021-08-02'), ('E1002', 'Microsoft 365', '2021-08-02'),
('E1002', 'SAP Finance', '2021-08-10'),
('E1003', 'Slack', '2024-01-20'), ('E1003', 'Zoom', '2024-01-20'), ('E1003', 'Microsoft 365', '2024-01-20'),
('E1003', 'Salesforce', '2024-01-22'),
('E1004', 'Slack', '2026-02-05'), ('E1004', 'Microsoft 365', '2026-02-05'), ('E1004', 'GitHub', '2026-02-06');

-- ---------------------------------------------------------------- service status
INSERT INTO service_status VALUES
('VPN',        'degraded',    'Pune gateway (vpn-pune) under planned maintenance until 18:00 IST today. Use the Mumbai gateway.', '2026-10-09 09:30'),
('Email',      'operational', 'All Microsoft 365 services are running normally.',                                                 '2026-10-09 08:00'),
('Wi-Fi',      'operational', 'All office networks are running normally.',                                                        '2026-10-09 08:00'),
('Printing',   'operational', 'Follow-Me Print is running normally.',                                                             '2026-10-09 08:00'),
('GitHub',     'operational', 'Running normally.',                                                                                '2026-10-09 08:00'),
('Jira',       'down',        'Jira is unavailable for everyone. The vendor is investigating. Next update at 13:00 IST.',          '2026-10-09 10:15'),
('Salesforce', 'operational', 'Running normally.',                                                                                '2026-10-09 08:00');

-- ---------------------------------------------------------------- tickets
INSERT INTO tickets VALUES
(5001, 'E1003', 'troubleshooting', 'P3', 'Outlook desktop app crashes when opening calendar',          'in_progress', 'Service Desk L1', '2026-10-06 11:20'),
(5002, 'E1001', 'troubleshooting', 'P4', 'Follow-Me Print does not recognise ID badge on 3rd floor',   'open',        'Service Desk L1', '2026-10-07 15:05'),
(5003, 'E1002', 'hardware',        'P3', 'ThinkPad T14 battery drains in under 2 hours',               'resolved',    'Service Desk L1', '2026-09-22 10:00');

-- ---------------------------------------------------------------- access requests
INSERT INTO access_requests VALUES
(7001, 'E1003', 'Tableau', 'restricted', 'Build quarterly pipeline dashboards', 'E1007 (manager)', 'approved', 'E1007', '2026-09-30 12:00');
