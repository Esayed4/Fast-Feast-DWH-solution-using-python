create database dwh_db
CREATE TABLE dim_driver (
    driver_sk    SERIAL PRIMARY KEY,           -- Surrogate Key (auto-incrementing)
    driver_id    INT NOT NULL,                 -- Natural Key (from source system)
    shift        VARCHAR(50),
    vehicle_type VARCHAR(50),
    hire_date    DATE,
    rating_avg   NUMERIC(3, 2),                -- More precise than float for ratings
    on_time_rate NUMERIC(5, 4),
    cancel_rate  NUMERIC(5, 4),
    is_active    BOOLEAN,
    start_date   DATE NOT NULL,
    end_date     DATE,                         -- NULL usually indicates the current record
    is_current   BOOLEAN DEFAULT TRUE
);

-- 1. Create dim_segment
CREATE TABLE dim_segment (
    segment_id       int PRIMARY KEY,
    segment_name     VARCHAR(100),
    discount_pct     NUMERIC(5, 2),
    priority_support BOOLEAN
);

-- 2. Create dim_category
CREATE TABLE dim_category (
     category_id     INT PRIMARY KEY,
    category_name    VARCHAR(100)
);

-- 3. Create dim_customer (SCD Type 2 structure)
CREATE TABLE dim_customer (
    customer_sk      SERIAL PRIMARY KEY,
    customer_id      INT NOT NULL,           -- Natural Key
    segment_id       INT REFERENCES dim_segment(segment_id),
    gender           VARCHAR(20),
    signup_date      DATE,
    start_date       DATE NOT NULL,
    end_date         DATE,
    is_current       BOOLEAN DEFAULT TRUE
);

-- 4. Create dim_restaurant
 
CREATE TABLE dim_restaurant (
     restaurant_id    INT primary key,
    restaurant_name  VARCHAR(255),
    category_id      INT REFERENCES dim_category(category_id),
    price_tier       VARCHAR(50),
    rating_avg       NUMERIC(3, 2),
    prep_time_avg_min NUMERIC(5, 2),
    is_active        BOOLEAN DEFAULT TRUE
);
 
 CREATE TABLE fact_orders (
    order_id            INT NOT NULL,              -- Removed PRIMARY KEY here
    order_date_id      INT,                       
    customer_sk         INT REFERENCES dim_customer(customer_sk),
    restaurant_id       INT REFERENCES dim_restaurant(restaurant_id),
    driver_sk           INT REFERENCES dim_driver(driver_sk),
    region_id           INT,
    order_time          TIMESTAMP,
    delivery_time       TIMESTAMP,
    row_timestamp       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    order_amount        NUMERIC(12, 2),
    status              VARCHAR(50),
    delivery_duration_min NUMERIC(8, 2),
    is_on_time          BOOLEAN
    -- Define the composite Primary Key here
 )  

-- 1. Create dim_team
CREATE TABLE dim_team (
     team_id    INT PRIMARY KEY,
    team_name  VARCHAR(100)
);

-- 2. Create dim_agent (SCD Type 2 structure)
CREATE TABLE dim_agent (
    agent_sk            SERIAL PRIMARY KEY,           -- Surrogate Key
    agent_id            INT NOT NULL,                 -- Natural Key
    team_id             INT REFERENCES dim_team(team_id),
    skill_level         VARCHAR(50),
    hire_date           DATE,
    avg_handle_time_min NUMERIC(8, 2),
    resolution_rate     NUMERIC(5, 4),                -- e.g., 0.9500 for 95%
    csat_score          NUMERIC(3, 2),                -- e.g., 4.50
    is_active           BOOLEAN,
    start_date          DATE NOT NULL,
    end_date            DATE,
    is_current          BOOLEAN DEFAULT TRUE
);

 
CREATE TABLE fact_tickets (
    ticket_id               INT PRIMARY KEY,           -- Natural Key
    order_id                INT,                       -- Reference to fact_orders or source
    created_date_id         INT,                       -- FK to dim_date (YYYYMMDD)
    customer_sk             INT ,
    restaurant_id           INT ,
    driver_sk               INT  ,
    region_id               INT,
    agent_sk                INT  ,
    reason_id               INT,
    priority_id             INT,
    channel_id              INT,
    ticket_create_time      TIMESTAMP,
    sla_first_due_at        TIMESTAMP,
    sla_resolve_due_at      TIMESTAMP,
    first_response_at       TIMESTAMP,
    resolved_at             TIMESTAMP,
    status                  VARCHAR(50),
    refund_amount           NUMERIC(12, 2),            -- Precision for currency
    resolved_on_time        BOOLEAN,
    resolve_from_creating_min NUMERIC(10, 2),
    resolve_from_response_min NUMERIC(10, 2),
    delay_of_resolving      NUMERIC(10, 2)
);




























