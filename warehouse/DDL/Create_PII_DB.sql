CREATE DATABASE pii_db;

CREATE SCHEMA PII;

CREATE TABLE PII.dim_customer_pii (
    customer_pii_sk  SERIAL PRIMARY KEY,
    customer_id      INT NOT NULL,
    full_name        VARCHAR(255),
    email            VARCHAR(255),
    phone            VARCHAR(50)
);

CREATE TABLE PII.dim_driver_pii (
    driver_pii_sk  SERIAL PRIMARY KEY,
    driver_id      INT NOT NULL,
    driver_name    VARCHAR(255),
    driver_phone   VARCHAR(50),
    national_id    VARCHAR(50)
);

CREATE TABLE PII.dim_agent_pii (
    agent_pii_sk  SERIAL PRIMARY KEY,
    agent_id      INT NOT NULL,
    agent_name    VARCHAR(255),
    agent_email   VARCHAR(255),
    agent_phone   VARCHAR(50)
);