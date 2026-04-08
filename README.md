


#  FastFeast — OLTP → OLAP Data Pipeline

A fault-tolerant Python pipeline that streams **FastFeast's** operational (OLTP) data into a clean analytical warehouse (OLAP). It handles data quality validation, PII masking, orphan record resolution, SLA monitoring, and revenue analytics — all in micro-batch ingestion cycles.

---

## 📋 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Key Features](#key-features)
- [Getting Started](#getting-started)
- [Configuration](#configuration)
- [Modules](#modules)
- [Data Warehouse Design](#data-warehouse-design)
- [Scripts](#scripts)
- [Running the Pipeline](#running-the-pipeline)

---

## Overview

FastFeast's transactional systems generate continuous order, ticket, customer, and driver data. This pipeline bridges the gap between raw OLTP records and a clean, analytics-ready OLAP warehouse by:

- Ingesting data in **micro-batches** and **streams**
- Validating schema and business rules before loading
- Masking sensitive **PII** before it touches the warehouse
- Quarantining bad records and resolving **orphan** dependencies
- Monitoring **SLA** compliance and exposing **revenue analytics**

---

## Architecture

```OLTP Source (FastFeast Operational DB)
                │
        ┌───────┴────────┐
        │                │
        ▼                ▼
 ┌─────────────┐  ┌──────────────────┐
 │   Watcher   │  │ Batch Scheduler  │
 │ (watcher.py)│  │(batch_scheduler  │
 │             │  │     .py)         │
 │             │  │                  │
 │  Detects    │  │  Triggers timed  │
 │  incoming   │  │  micro-batch     │
 │  STREAM     │  │  BATCH runs      │
 │  data files │  │  on a schedule   │
 └──────┬──────┘  └────────┬─────────┘
        │                  │
        ▼                  ▼
 ┌─────────────┐    ┌──────────────┐
 │   Stream    │    │    Batch     │
 │  Pipeline   │    │   Pipeline   │
 └──────┬──────┘    └──────┬───────┘
        │                  │
        └────────┬──────────┘
                 │
                 ▼
        ┌─────────────┐
        │   Reader    │  ← Extracts raw records (extractor.py)
        └──────┬──────┘
               │
               ▼
       ┌──────────────────┐
       │   Validators     │  ← Schema + Business rule checks
       │                  │         │
       │                  │         ▼ (on failure)
       │                  │   ┌─────────────┐
       │                  │   │  Quarantine │
       └──────┬───────────┘   └─────────────┘
              │
              ▼
       ┌──────────────────┐
       │   Transformer    │  ← Dedup, SCD2, dim_date, order/ticket transforms
       └──────┬───────────┘
              │
              ▼
       ┌──────────────────┐
       │     Loader       │  ← PII masking, orphan handling, DB write
       └──────┬───────────┘
              │
              ▼
       ┌──────────────────┐
       │  OLAP Warehouse  │  ← Galaxy Schema (fact + dimension tables)
       └──────────────────┘
              │
              ▼
        ┌──────────────────────┐
        │  Orphan Recheck      │  ← Re-validates    orphan records after
        │  (post-batch loader) │    each batch completes
        └──────────────────────┘
 └──────────────────┘
```

---

## Project Structure

```
fastfeast-pipeline/
│
├── config/
│   ├── logging_config.py       # Logging configuration
│   ├── schemas.py              # Data schema definitions
│   └── settings.py             # Global settings & environment vars
│
├── data/                       # Raw / intermediate data files
│
├── loader/
│   ├── Handle_Orphan_after_loading_batch.py  # Orphan record resolution
│   ├── PII_writer.py           # PII masking before warehouse write
│   ├── connect_to_db.py        # Database connection management
│   ├── load_batch_data.py      # Batch ingestion loader
│   └── load_stream_data.py     # Stream ingestion loader
│
├── logger/
│   ├── alert_handler.py        # SLA breach & error alerting
│   └── pipeline_logger.py      # Structured pipeline logging
│
├── orchestrator/
│   ├── batch_pipeline.py       # Orchestrates full batch pipeline run
│   └── stream_pipeline.py      # Orchestrates streaming pipeline run
│
├── reader/
│   ├── __init__.py
│   └── extractor.py            # OLTP data extraction logic
│
├── scripts/
│   ├── add_new_customers.py    # Seed / update customer records
│   ├── add_new_drivers.py      # Seed / update driver records
│   ├── generate_batch_data.py  # Generate synthetic batch data
│   ├── generate_master_data.py # Generate master/reference data
│   ├── generate_stream_data.py # Generate synthetic streaming data
│   └── simulate_day.py         # Simulate a full operational day
│
├── transformer/
│   ├── deduplicator.py         # Duplicate record detection & removal
│   ├── generate_dim_date.py    # Date dimension table generator
│   ├── scd2.py                 # Slowly Changing Dimension Type 2 logic
│   ├── transform_order.py      # Order fact transformation
│   └── transform_tickets.py    # Ticket fact transformation
│
├── validators/
│   ├── business_validator.py   # Business rule validation
│   ├── quarantine_writer.py    # Writes failed records to quarantine
│   └── schema_validator.py     # Schema / data type validation
│
├── warehouse/
│   ├── DDL/
│   │   ├── Create Orphan DBs.sql  # DDL for orphan staging tables
│   │   ├── Create Tables.sql      # Main warehouse DDL
│   │   └── Create_PII_DB.sql      # PII vault database DDL
│   ├── DWH design/
│   │   ├── DWH Galaxy Schema.png  # Visual warehouse schema diagram
│   │   └── DWH-design.mmd         # Mermaid source for schema
│   ├── OLAP Documentations/
│   │   ├── Document OLAP loading Strategy.docx
│   │   ├── Documentation OLAP architecture.docx
│   │   └── Documentation.Choice The Best DBMS for the project.rtf
│   └── __init__.py
│
├── watchers/
│   ├── batch_detector.py       # Detects new batch files to process
│   ├── batch_scheduler.py      # Schedules micro-batch execution
│   └── watcher.py              # Main file system watcher
│
├── main.py                     # Pipeline entry point
├── docker-compose.yml          # Docker services definition
├── requirements.txt            # Python dependencies
├── Project Structure.txt       # Raw project structure reference
└── .gitignore
```

---

## Key Features

### Data Quality Validation
- **Schema validation** — enforces column types, nullability, and structure via `schema_validator.py`
- **Business rule validation** — domain-specific checks (e.g., valid order amounts, driver assignments) via `business_validator.py`
- **Quarantine** — invalid records are written to a quarantine store instead of failing the pipeline

###  PII Masking
- Sensitive customer fields are masked/anonymized by `PII_writer.py` before being written to the warehouse
- A dedicated `PII_DB` stores vaulted identifiers separately (see `Create_PII_DB.sql`)

###  Orphan Record Handling
- Records referencing non-existent parents (e.g., orders with unknown customers) are staged in orphan tables
- `Handle_Orphan_after_loading_batch.py` resolves orphans after each batch completes

###  Fault-Tolerant Micro-Batch Ingestion
- The `watchers/` layer detects new data files and triggers batch runs on a schedule
- Failures are isolated per batch — a single bad batch does not halt the pipeline
- Both batch (`batch_pipeline.py`) and stream (`stream_pipeline.py`) modes are supported

### SLA Monitoring & Alerting
- `pipeline_logger.py` tracks ingestion timing and throughput per run
- `alert_handler.py` fires alerts when SLA thresholds are breached

###  SCD Type 2 Support
- Slowly Changing Dimensions are managed in `scd2.py` to preserve historical dimension records

### Date Dimension
- Auto-generated date dimension via `generate_dim_date.py` for time-series analytics
###  Pipeline Logging
- structured start/end summaries with full run metrics
###  Real-Time Email Alerting 
- root logger hook, daemon threads, auto-triggered alerts, and SMTP config details
---

## Getting Started

### Prerequisites
- Python 
- Docker & Docker Compose
- PostgreSQL (or configured DBMS — see warehouse documentation)

### Installation

```bash
# Clone the repository
git clone https://github.com/your-org/fastfeast-pipeline.git
cd fastfeast-pipeline

# Install Python dependencies
pip install -r requirements.txt  << empty file

# Start infrastructure services (DB, etc.)
docker-compose up -d
```

### Initialize the Warehouse

```bash
# Run DDL scripts in order
psql -f warehouse/DDL/"Create Tables.sql"
psql -f warehouse/DDL/"Create Orphan DBs.sql"
psql -f warehouse/DDL/"Create_PII_DB.sql"
```



---


## Modules

### Reader
Extracts records from the OLTP source. The `extractor.py` module handles connection management and incremental extraction.

### Validators
Two-stage validation:
1. `schema_validator.py` — structural/type checks
2. `business_validator.py` — domain rule checks

Failures are routed to `quarantine_writer.py`.

### Transformer
Transforms raw records into warehouse-ready facts and dimensions:
- **Deduplication** — removes duplicate records before load
- **SCD2** — tracks historical changes on slowly changing dimensions
- **Order & Ticket transforms** — shapes OLTP records into fact table format
- **Date dimension** — populates `dim_date` for analytical queries

### Loader
Writes clean, transformed records to the warehouse:
- **PII masking** applied at write time
- **Orphan resolution** run post-batch
- Supports both batch and stream write modes

### Orchestrator
Ties all stages together:
- `batch_pipeline.py` — full ETL run for a batch
- `stream_pipeline.py` — continuous streaming ingestion

### Watchers
File system watchers that trigger pipeline runs:
- `batch_detector.py` — identifies new data files
- `batch_scheduler.py` — manages timing and scheduling
- `watcher.py` — main watcher process

### Logger

The `logger/` module handles structured pipeline observability across two files.

**`pipeline_logger.py`** logs pipeline-level summaries at the start and end of each run:
- `log_pipeline_start(run_date)` — marks the beginning of a daily run
- `log_pipeline_end(...)` — emits a full summary including total files processed, rows loaded, rows valid, rows quarantined, and total duration in seconds

### Alert 
provides real-time error alerting via email using multi-threading:
- `register_alert_handler()` — called once at pipeline startup in the orchestrator; attaches a custom `logging.Handler` to the root logger at `ERROR` level
- Any `logger.error()` call anywhere in the pipeline automatically triggers an email alert
- Emails are dispatched in **daemon threads** so alert delivery never blocks the pipeline
- Each alert email includes the module name, function, line number, and full error message for fast debugging
 

---

## Data Warehouse Design

The warehouse follows a **Galaxy Schema** (multiple fact tables sharing conformed dimensions).

See the visual design at `warehouse/DWH design/DWH Galaxy Schema.png`.

Key tables:
- `fact_orders` — core order transactions
- `fact_tickets` — support/delivery tickets
- `dim_customer` — customer dimension (SCD2)
- `dim_driver` — driver dimension (SCD2)
- `dim_date` — date dimension for time-series slicing
- Orphan staging tables — temporary holding for unresolved foreign keys

For DBMS selection rationale and architecture decisions, see `warehouse/OLAP Documentations/`.

---

## Scripts

| Script | Purpose |
|---|---|
| `simulate_day.py` | Simulates a full day of FastFeast operations end-to-end |
| `generate_batch_data.py` | Generates synthetic batch records for testing |
| `generate_stream_data.py` | Generates synthetic streaming records |
| `generate_master_data.py` | Generates master/reference data (menus, zones, etc.) |
| `add_new_customers.py` | Adds new customer records to the OLTP source |
| `add_new_drivers.py` | Adds new driver records to the OLTP source |

---

## Running the Pipeline
```bash
 python main.py watch
```


## Docker


The `docker-compose.yml` spins up a PostgreSQL 15 instance as the OLAP warehouse.

### Services

| Service | Container | Port | Network |
|---|---|---|---|
| PostgreSQL 15 | `postgres_dwh` | `5432:5432` | `dwh_network` |

### Default Credentials

| Parameter | Value |
|---|---|
| User | `admin` |
| Password | `admin` |




---

