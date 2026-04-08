CREATE DATABASE dwh_db;
CREATE SCHEMA DWH;

CREATE TABLE DWH.dim_segment (
    segment_id       INT PRIMARY KEY,
    segment_name     VARCHAR(100),
    discount_pct     NUMERIC(5, 2),
    priority_support BOOLEAN
);

CREATE TABLE DWH.dim_category (
    category_id   INT PRIMARY KEY,
    category_name VARCHAR(100)
);

CREATE TABLE DWH.dim_team (
    team_id   INT PRIMARY KEY,
    team_name VARCHAR(100)
);

CREATE TABLE DWH.dim_city (
    city_id   INT PRIMARY KEY,
    city_name VARCHAR(100),
    country   VARCHAR(100),
    timezone  VARCHAR(100)
);

CREATE TABLE DWH.dim_region (
    region_id         INT PRIMARY KEY,
    region_name       VARCHAR(100),
    city_id           INT,
    delivery_base_fee NUMERIC(8, 2)
);

CREATE TABLE DWH.dim_reason (
    reason_id          INT PRIMARY KEY,
    reason_name        VARCHAR(255),
    reason_category_id INT,
    severity_level     VARCHAR(50),
    typical_refund_pct NUMERIC(5, 2)
);

CREATE TABLE DWH.dim_priority (
    priority_id            INT PRIMARY KEY,
    priority_code          VARCHAR(50),
    priority_name          VARCHAR(100),
    sla_first_response_min INT,
    sla_resolution_min     INT
);

CREATE TABLE DWH.dim_customer (
    customer_sk  SERIAL PRIMARY KEY,
    customer_id  INT NOT NULL,
    segment_id   INT REFERENCES DWH.dim_segment(segment_id),
    gender       VARCHAR(20),
    signup_date  DATE,
    start_date   DATE NOT NULL,
    end_date     DATE,
    is_current   BOOLEAN DEFAULT TRUE
);

CREATE TABLE DWH.dim_driver (
    driver_sk    SERIAL PRIMARY KEY,
    driver_id    INT NOT NULL,
    shift        VARCHAR(50),
    vehicle_type VARCHAR(50),
    hire_date    DATE,
    rating_avg   NUMERIC(3, 2),
    on_time_rate NUMERIC(5, 4),
    cancel_rate  NUMERIC(5, 4),
    is_active    BOOLEAN,
    start_date   DATE NOT NULL,
    end_date     DATE,
    is_current   BOOLEAN DEFAULT TRUE
);

CREATE TABLE DWH.dim_restaurant (
    restaurant_id     INT PRIMARY KEY,
    restaurant_name   VARCHAR(255),
    category_id       INT REFERENCES DWH.dim_category(category_id),
    price_tier        VARCHAR(50),
    rating_avg        NUMERIC(3, 2),
    prep_time_avg_min NUMERIC(5, 2),
    is_active         BOOLEAN DEFAULT TRUE
);

CREATE TABLE DWH.dim_agent (
    agent_sk            SERIAL PRIMARY KEY,
    agent_id            INT NOT NULL,
    team_id             INT REFERENCES DWH.dim_team(team_id),
    skill_level         VARCHAR(50),
    hire_date           DATE,
    avg_handle_time_min NUMERIC(8, 2),
    resolution_rate     NUMERIC(5, 4),
    csat_score          NUMERIC(3, 2),
    is_active           BOOLEAN,
    start_date          DATE NOT NULL,
    end_date            DATE,
    is_current          BOOLEAN DEFAULT TRUE
);

CREATE TABLE DWH.dim_date (
    date_id     INT PRIMARY KEY,
    full_date   DATE,
    day_of_week VARCHAR(20),
    month       INT,
    month_name  VARCHAR(20),
    quarter     INT,
    year        INT,
    is_weekend  BOOLEAN
);

CREATE TABLE DWH.fact_orders (
    order_id              VARCHAR(50) NOT NULL,
    order_date_id         INT,
    customer_sk           INT  ,
    restaurant_id         INT  ,
    driver_sk             INT  ,
    region_id             INT,
    order_time            VARCHAR(50),
    delivery_time         VARCHAR(50),
    row_timestamp         VARCHAR(50) ,
    order_amount          NUMERIC(12, 2),
    status                VARCHAR(50),
    delivery_duration_min NUMERIC(8, 2),
    is_on_time            BOOLEAN
);

CREATE TABLE DWH.fact_tickets (
    ticket_id                 VARCHAR(50) PRIMARY KEY,
    order_id                  VARCHAR(50),
    created_date_id           INT,
    customer_sk               INT,
    restaurant_id             INT,
    driver_sk                 INT,
    region_id                 INT,
    agent_sk                  INT,
    reason_id                 INT,
    priority_id               INT,
    channel_id                INT,
    ticket_create_time        VARCHAR(50),
    sla_first_due_at          VARCHAR(50),
    sla_resolve_due_at        VARCHAR(50),
    first_response_at         VARCHAR(50),
    resolved_at               VARCHAR(50),
    status                    VARCHAR(50),
    refund_amount             NUMERIC(12, 2),
    resolved_on_time          BOOLEAN,
    resolve_from_creating_min NUMERIC(10, 2),
    resolve_from_response_min NUMERIC(10, 2),
    delay_of_resolving        NUMERIC(10, 2)
);