CREATE DATABASE orphan_db;
CREATE SCHEMA orphan;

CREATE TABLE orphan.orphan_fact_orders (
    orphan_id           SERIAL PRIMARY KEY,
    rejection_reason    TEXT,                -- Detailed error message
    unmatched_fk_count  INT DEFAULT 0,       -- Number of failed lookups
    rejected_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Data columns
    order_id             VARCHAR(50) NOT NULL,              -- Removed PRIMARY KEY here
    order_date_id          int,             
    customer_id        INT ,
    restaurant_id    INT ,
    driver_id           INT  ,
    region_id           INT,
    order_time           VARCHAR(50),
    delivery_time        VARCHAR(50),
    row_timestamp        VARCHAR(50)  ,
    order_amount         NUMERIC(12, 2),
    status                VARCHAR(50),
    delivery_duration_min NUMERIC(8, 2),
    is_on_time            BOOLEAN,
    is_customer_sk_orphan BOOLEAN DEFAULT FALSE,
    is_restaurant_sk_orphan BOOLEAN DEFAULT FALSE,
    is_driver_sk_orphan BOOLEAN DEFAULT FALSE
);


  
CREATE TABLE orphan.orphan_fact_tickets (
    orphan_id           SERIAL PRIMARY KEY,
    rejection_reason    TEXT,
    unmatched_fk_count  INT DEFAULT 0,
    
    ticket_id                VARCHAR(50) ,           
    order_id                 VARCHAR(50),                       -- Reference to fact_orders or source
    created_date_id         INT,                       -- FK to dim_date (YYYYMMDD)
    customer_id             INT  ,
    restaurant_id           INT  ,
    driver_id               INT  ,
    region_id               INT,
    agent_id                INT  ,
    reason_id               INT,
    priority_id             INT,
    channel_id              INT,
    ticket_create_time       VARCHAR(50),
    sla_first_due_at         VARCHAR(50),
    sla_resolve_due_at       VARCHAR(50),
    first_response_at        VARCHAR(50),
    resolved_at              VARCHAR(50),
    status                   VARCHAR(50),
    refund_amount           NUMERIC(12, 2),            -- Precision for currency
    resolved_on_time        BOOLEAN,
    resolve_from_creating_min NUMERIC(10, 2),
    resolve_from_response_min NUMERIC(10, 2),
    delay_of_resolving      NUMERIC(10, 2),
    is_order_id_orphan BOOLEAN DEFAULT FALSE,
    is_agent_sk_orphan BOOLEAN DEFAULT FALSE
);