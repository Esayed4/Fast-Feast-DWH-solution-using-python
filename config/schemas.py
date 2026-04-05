# Single source of truth for every table in the pipeline.

# data type constants for readability

INT = "int64"
FLT = "float64"
STR = "object"
BOOL = "bool"
DATE = "date"
DT = "datetime64[ns]"

# =============================================================================

# BATCH DIMENSION TABLES

CITIES_SCHEMA = {
    "source_file": "cities.json",
    "primary_key": "city_id",
    "required_columns": ["city_id", "city_name", "country", "timezone"],
    "dtypes": {
        "city_id": INT,
        "city_name": STR,
        "country": STR,
        "timezone": STR,
    }
}

REGIONS_SCHEMA = {
    "source_file": "regions.csv",
    "primary_key": "region_id",
    "required_columns": ["region_id", "region_name", "city_id", "delivery_base_fee"],
    "dtypes": {
        "region_id": INT,
        "region_name": STR,
        "city_id": INT,
        "delivery_base_fee": FLT,
    },
    "foreign_keys": {"city_id": "cities"}
}

SEGMENTS_SCHEMA = {
    "source_file": "segments.csv",
    "primary_key": "segment_id",
    "required_columns": ["segment_id", "segment_name", "discount_pct", "priority_support"],
    "dtypes": {
        "segment_id": INT,
        "segment_name": STR,
        "discount_pct": FLT,
        "priority_support": BOOL,
    }
}

CUSTOMERS_SCHEMA = {
    "source_file": "customers.csv",
    "primary_key": "customer_id",
    "required_columns": [
        "customer_id", "full_name", "email", "phone",
        "segment_id", "signup_date", "gender"
    ],
    "dtypes": {
        "customer_id": INT,
        "full_name":   STR,
        "email":       STR,
        "phone":       STR,
        "segment_id":  INT,
        "signup_date": STR,
        "gender":      STR,
    },
    "pii_columns": ["full_name", "email", "phone"],
    "foreign_keys": {
        "segment_id": "segments",
    },
    "dwh_columns": ["customer_id", "segment_id", "gender", "signup_date"]
}

CATEGORIES_SCHEMA = {
    "source_file": "categories.csv",
    "primary_key": "category_id",
    "required_columns": ["category_id", "category_name"],
    "dtypes": {
        "category_id": INT,
        "category_name": STR,
    }
}

RESTAURANTS_SCHEMA = {
    "source_file": "restaurants.json",
    "primary_key": "restaurant_id",
    "required_columns": [
        "restaurant_id", "restaurant_name", "region_id",
        "category_id", "price_tier", "rating_avg",
        "prep_time_avg_min", "is_active", "created_at", "updated_at"
    ],
    "dtypes": {
        "restaurant_id": FLT,
        "restaurant_name": STR,
        "region_id": INT,
        "category_id": INT,
        "price_tier": STR,
        "rating_avg": FLT,
        "prep_time_avg_min": INT,
        "is_active": BOOL,
        "created_at": DT,
        "updated_at": DT,
    },
    "foreign_keys": {"region_id": "regions", "category_id": "categories"},
}

DRIVERS_SCHEMA = {
    "source_file": "drivers.csv",
    "primary_key": "driver_id",
    "required_columns": [
        "driver_id", "driver_name", "driver_phone", "national_id", "region_id",
        "shift", "vehicle_type", "hire_date",
        "rating_avg", "on_time_rate", "cancel_rate", "is_active", "created_at", "updated_at"
    ],
    "dtypes": {
        "driver_id": INT,
        "driver_name": STR,
        "driver_phone": STR,
        "national_id": STR,
        "region_id": INT,
        "shift": STR,
        "vehicle_type": STR,
        "hire_date": DATE,
        "rating_avg": FLT,
        "on_time_rate": FLT,
        "cancel_rate": FLT,
        "is_active": BOOL,
        "created_at": DT,
        "updated_at": DT,
    },
    "pii_columns":  ["driver_name", "driver_phone", "national_id"],
    "foreign_keys": {"region_id": "regions"},
    "dwh_columns":  [
        "driver_id", "shift", "vehicle_type", "hire_date",
        "rating_avg", "on_time_rate", "cancel_rate", "is_active",
    ],
}

TEAMS_SCHEMA = {
    "source_file": "teams.csv",
    "primary_key": "team_id",
    "required_columns": ["team_id", "team_name"],
    "dtypes": {
        "team_id":   INT,
        "team_name": STR,
    },
}

AGENTS_SCHEMA = {
    "source_file": "agents.csv",
    "primary_key": "agent_id",
    "required_columns": [
        "agent_id", "agent_name", "agent_email", "agent_phone",
        "team_id", "skill_level", "hire_date","avg_handle_time_min", 
        "resolution_rate", "csat_score", "is_active", "created_at", "updated_at"
    ],
    "dtypes": {
        "agent_id": INT,
        "agent_name": STR,
        "agent_email": STR,
        "agent_phone": STR,
        "team_id": INT,
        "skill_level": STR,
        "hire_date": DATE,
        "avg_handle_time_min": INT,
        "resolution_rate": FLT,
        "csat_score": FLT,
        "is_active": BOOL,
        "created_at": DT,
        "updated_at": DT,
    },
    "pii_columns": ["agent_name", "agent_email", "agent_phone"],
    "foreign_keys": {"team_id": "teams"},
    "dwh_columns": [
        "agent_id", "team_id", "skill_level", "hire_date",
        "avg_handle_time_min", "resolution_rate", "csat_score", "is_active",
    ]
}

REASON_CATEGORIES_SCHEMA = {
    "source_file": "reason_categories.csv",
    "primary_key": "reason_category_id",
    "required_columns": ["reason_category_id", "category_name"],
    "dtypes": {
        "reason_category_id": INT,
        "category_name": STR,
    }
}

REASONS_SCHEMA = {
    "source_file": "reasons.csv",
    "primary_key": "reason_id",
    "required_columns": [
        "reason_id", "reason_name", "reason_category_id",
        "severity_level", "typical_refund_pct",
    ],
    "dtypes": {
        "reason_id": INT,
        "reason_name": STR,
        "reason_category_id": INT,
        "severity_level": INT,
        "typical_refund_pct": FLT,
    },
    "foreign_keys": {"reason_category_id": "reason_categories"}
}

PRIORITIES_SCHEMA = {
    "source_file": "priorities.csv",
    "primary_key": "priority_id",
    "required_columns": [
        "priority_id", "priority_code", "priority_name",
        "sla_first_response_min", "sla_resolution_min",
    ],
    "dtypes": {
        "priority_id": INT,
        "priority_code": STR,
        "priority_name": STR,
        "sla_first_response_min": INT,
        "sla_resolution_min": INT,
    }
}

CHANNELS_SCHEMA = {
    "source_file": "channels.csv",
    "primary_key": "channel_id",
    "required_columns": ["channel_id", "channel_name"],
    "dtypes": {
        "channel_id": INT,
        "channel_name": STR,
    }
}

# =============================================================================

# STREAM FACT TABLES

ORDERS_SCHEMA = {
    "source_file": "orders.json",
    "primary_key": "order_id",
    "required_columns": [
        "order_id", "customer_id", "restaurant_id", "driver_id", "region_id",
        "order_amount", "delivery_fee", "discount_amount", "total_amount",
        "order_status", "payment_method", "order_created_at", "delivered_at",
    ],
    "dtypes": {
        "order_id": STR,
        "customer_id": INT,
        "restaurant_id": FLT,
        "driver_id": INT,
        "region_id": INT,
        "order_amount": FLT,
        "delivery_fee": FLT,
        "discount_amount": FLT,
        "total_amount": FLT,
        "order_status": STR,
        "payment_method": STR,
        "order_created_at": DT,
        "delivered_at": DT,
    },
    "foreign_keys": {
        "customer_id":   "customers",
        "restaurant_id": "restaurants",
        "driver_id":     "drivers",
        "region_id":     "regions",
    }
}
 
TICKETS_SCHEMA = {
    "source_file": "tickets.csv",
    "primary_key": "ticket_id",
    "required_columns": [
        "ticket_id", "order_id", "customer_id", "driver_id", "restaurant_id",
        "agent_id", "reason_id", "priority_id", "channel_id",
        "status", "refund_amount",
        "created_at", "first_response_at", "resolved_at",
        "sla_first_due_at", "sla_resolve_due_at",
    ],
    "dtypes": {
        "ticket_id": STR,
        "order_id": STR,
        "customer_id": INT,
        "driver_id": INT,
        "restaurant_id": FLT,
        "agent_id": INT,
        "reason_id": INT,
        "priority_id": INT,
        "channel_id": INT,
        "status": STR,
        "refund_amount": FLT,
        "created_at": DT,
        "first_response_at": DT,
        "resolved_at": DT,
        "sla_first_due_at": DT,
        "sla_resolve_due_at": DT,
    },
    "foreign_keys": {
        "order_id":      "orders",
        "customer_id":   "customers",
        "restaurant_id": "restaurants",
        "driver_id":     "drivers",
        "agent_id":      "agents",
        "reason_id":     "reasons",
        "priority_id":   "priorities",
        "channel_id":    "channels",
    }
}
 
TICKET_EVENTS_SCHEMA = {
    "source_file": "ticket_events.json",
    "primary_key": "event_id",
    "required_columns": [
        "event_id", "ticket_id", "agent_id",
        "event_ts", "old_status", "new_status", "notes",
    ],
    "dtypes": {
        "event_id": STR,
        "ticket_id": STR,
        "agent_id": INT,
        "event_ts": DT,
        "old_status": STR,
        "new_status": STR,
        "notes": STR,
    },
    "foreign_keys": {
        "ticket_id": "tickets",
        "agent_id":  "agents",
    }
}

# =============================================================================

# REGISTRY: maps table name with schema dict to look up schemas dynamically

SCHEMA_REGISTRY = {
    # batch dims
    "cities": CITIES_SCHEMA,
    "regions": REGIONS_SCHEMA,
    "segments": SEGMENTS_SCHEMA,
    "customers": CUSTOMERS_SCHEMA,
    "categories": CATEGORIES_SCHEMA,
    "restaurants": RESTAURANTS_SCHEMA,
    "drivers": DRIVERS_SCHEMA,
    "teams": TEAMS_SCHEMA,
    "agents": AGENTS_SCHEMA,
    "reason_categories": REASON_CATEGORIES_SCHEMA,
    "reasons": REASONS_SCHEMA,
    "priorities": PRIORITIES_SCHEMA,
    "channels": CHANNELS_SCHEMA,
    # stream facts
    "orders": ORDERS_SCHEMA,
    "tickets": TICKETS_SCHEMA,
    "ticket_events": TICKET_EVENTS_SCHEMA,
}
