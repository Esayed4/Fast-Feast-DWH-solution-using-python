# tests/test_validators.py
"""
Test suite for schema and business validators
"""

import pytest
import pandas as pd
from datetime import datetime
import sys
from pathlib import Path

# Add project root to path if needed
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from pipeline.validators.schema_validator import schema_validate
from pipeline.validators.business_validator import business_validate
from config.schemas import SCHEMA_REGISTRY


def test_missing_columns():
    """Test that missing required columns cause full rejection"""
    df = pd.DataFrame({
        "city_id": [1, 2],
        "city_name": ["Cairo", "Alex"]  # Missing "country" and "timezone"
    })
    
    clean_df, rejected_df, metrics = schema_validate(df, "cities")
    
    assert clean_df.empty
    assert len(rejected_df) == 2
    assert "Missing required columns" in rejected_df["rejection_reason"].iloc[0]
    assert metrics["missing_columns"] == ["country", "timezone"]
    assert metrics["row_in"] == 2


def test_null_required_columns():
    """Test that nulls in required columns are rejected"""
    df = pd.DataFrame({
        "city_id": [1, 2, 3],
        "city_name": ["Cairo", None, "Alex"],
        "country": ["Egypt", "Egypt", None],
        "timezone": ["UTC+2", "UTC+2", "UTC+2"]
    })
    
    clean_df, rejected_df, metrics = schema_validate(df, "cities")
    
    assert len(clean_df) == 1  # Only first row
    assert len(rejected_df) == 2
    assert metrics["null_counts"]["city_name"] == 1
    assert metrics["null_counts"]["country"] == 1
    assert metrics["row_in"] == 3


def test_duplicate_pk():
    """Test duplicate primary key handling"""
    df = pd.DataFrame({
        "city_id": [1, 1, 2, 2, 3],
        "city_name": ["Cairo", "Cairo", "Alex", "Alex", "Mansoura"],
        "country": ["Egypt", "Egypt", "Egypt", "Egypt", "Egypt"],
        "timezone": ["UTC+2", "UTC+2", "UTC+2", "UTC+2", "UTC+2"]
    })
    
    clean_df, rejected_df, metrics = schema_validate(df, "cities")
    
    # Should keep first of each duplicate
    assert len(clean_df) == 3  # IDs: 1,2,3
    assert len(rejected_df) == 2  # Duplicates of 1 and 2
    assert metrics["duplicate_counts"] == 2
    assert metrics["row_in"] == 5


def test_dtype_validation_int():
    """Test integer dtype validation"""
    df = pd.DataFrame({
        "city_id": ["1", "2", "abc", "3"],  # Removed None to have exactly 1 invalid
        "city_name": ["Cairo", "Alex", "Giza", "Mansoura"],
        "country": ["Egypt"] * 4,
        "timezone": ["UTC+2"] * 4
    })
    
    clean_df, rejected_df, metrics = schema_validate(df, "cities")
    
    # Row with "abc" should be rejected
    assert len(clean_df) == 3  # Valid ints: 1,2,3
    assert len(rejected_df) == 1  # "abc" row
    assert metrics["dtype_fails"]["city_id"] == 1
    assert metrics["row_in"] == 4


def test_dtype_validation_float():
    """Test float dtype validation"""
    df = pd.DataFrame({
        "region_id": [1, 2, "3.5", "abc", 5],
        "region_name": ["North", "South", "East", "West", "Central"],
        "city_id": [1, 1, 2, 2, 3],
        "delivery_base_fee": [10.5, 12.0, 8.5, "invalid", 9.0]
    })
    
    clean_df, rejected_df, metrics = schema_validate(df, "regions")
    
    assert metrics["dtype_fails"]["delivery_base_fee"] == 1
    assert len(rejected_df) == 1
    assert metrics["row_in"] == 5


def test_dtype_validation_bool():
    """Test boolean dtype validation"""
    df = pd.DataFrame({
        "segment_id": [1, 2, 3, 4],
        "segment_name": ["Gold", "Silver", "Bronze", "Platinum"],
        "discount_pct": [10.0, 5.0, 2.5, 15.0],
        "priority_support": ["true", "false", "yes", "invalid"]
    })
    
    clean_df, rejected_df, metrics = schema_validate(df, "segments")
    
    # Last row with "invalid" should be rejected
    assert metrics["dtype_fails"]["priority_support"] == 1
    assert len(rejected_df) == 1
    assert metrics["row_in"] == 4


def test_dtype_validation_date():
    """Test date dtype validation"""
    df = pd.DataFrame({
        "customer_id": [1, 2, 3],
        "full_name": ["John", "Jane", "Bob"],
        "email": ["a@b.com", "c@d.com", "e@f.com"],
        "phone": ["123", "456", "789"],
        "region_id": [1, 2, 3],
        "segment_id": [1, 1, 2],
        "signup_date": ["2023-01-01", "invalid_date", "2023-03-01"],
        "gender": ["M", "F", "M"],
        "created_at": ["2023-01-01 10:00", "2023-01-02 11:00", "2023-01-03 12:00"],
        "updated_at": ["2023-01-01 10:00", "2023-01-02 11:00", "2023-01-03 12:00"]
    })
    
    clean_df, rejected_df, metrics = schema_validate(df, "customers")
    
    assert metrics["dtype_fails"]["signup_date"] == 1
    assert len(rejected_df) == 1
    assert metrics["row_in"] == 3

# tests/test_validators.py

def test_combined_validations_cleaner():
    """Test multiple rejection reasons without duplicates interfering"""
    df = pd.DataFrame({
        "city_id": [1, "abc", 2],  # Row 2 has dtype issue
        "city_name": ["Cairo", "Giza", None],  # Row 3 has null
        "country": ["Egypt", "Egypt", "Egypt"],
        "timezone": ["UTC+2", "UTC+2", "UTC+2"]
    })
    
    clean_df, rejected_df, metrics = schema_validate(df, "cities")
    
    # Only first row should be clean
    assert len(clean_df) == 1  # Only row 1 passes
    assert len(rejected_df) == 2  # Rows 2 and 3 rejected
    assert metrics["row_in"] == 3
    
    # Check dtype failure
    assert "city_id" in metrics["dtype_fails"]
    assert metrics["dtype_fails"]["city_id"] == 1
    
    # Check null failure
    assert metrics["null_counts"]["city_name"] == 1
    
    # Check rejection reasons
    reasons = rejected_df["rejection_reason"].tolist()
    print(f"\nRejection reasons: {reasons}")
    
    # Row 2 should have dtype_fail
    assert any("dtype_fail" in r or "int64" in r for r in reasons)
    
    # Row 3 should have Null
    assert any("Null" in r for r in reasons)
    
def test_empty_dataframe():
    """Test empty dataframe handling"""
    df = pd.DataFrame(columns=["city_id", "city_name", "country", "timezone"])
    
    clean_df, rejected_df, metrics = schema_validate(df, "cities")
    
    assert clean_df.empty
    assert rejected_df.empty
    assert metrics["row_in"] == 0


def test_schema_not_found():
    """Test handling of missing schema"""
    df = pd.DataFrame({"col1": [1, 2]})
    
    clean_df, rejected_df, metrics = schema_validate(df, "nonexistent_table")
    
    # The validator should handle missing schema gracefully
    assert clean_df.empty
    assert len(rejected_df) == 2  # All rows rejected due to no schema
    assert metrics["row_in"] == 2


def test_business_email_validation():
    """Test business validation for email format"""
    df = pd.DataFrame({
        "customer_id": [1, 2, 3],
        "full_name": ["John Doe", "Jane Doe", "Bob Smith"],
        "email": ["john@example.com", "invalid-email", "jane@test.com"],
        "phone": ["01157344478", "01157344478", "01157344478"],  # Simple digits
        "region_id": [1, 1, 1],
        "segment_id": [1, 1, 1],
        "signup_date": ["2023-01-01", "2023-01-01", "2023-01-01"],
        "gender": ["M", "F", "M"],
        "created_at": [datetime.now(), datetime.now(), datetime.now()],
        "updated_at": [datetime.now(), datetime.now(), datetime.now()]
    })
    
    # First run schema validation
    clean_schema, rejected_schema, schema_metrics = schema_validate(df, "customers")
    
    # Then run business validation
    clean_business, rejected_business, business_metrics = business_validate(clean_schema, "customers")
    
    # Only email validation should fail for row 2
    assert len(rejected_business) == 1
    assert "email_invalid" in business_metrics["checks"]
    assert "email" in business_metrics["checks"]["email_invalid"]
    assert business_metrics["checks"]["email_invalid"]["email"] == 1


def test_business_phone_validation():
    """Test business validation for phone format"""
    df = pd.DataFrame({
        "customer_id": [1, 2, 3],
        "full_name": ["John Doe", "Jane Doe", "Bob Smith"],
        "email": ["john@test.com", "jane@test.com", "bob@test.com"],
        "phone": ["invalid", "01127713166"],  # Simple valid and invalid
        "region_id": [1, 1, 1],
        "segment_id": [1, 1, 1],
        "signup_date": ["2023-01-01", "2023-01-01", "2023-01-01"],
        "gender": ["M", "F", "M"],
        "created_at": [datetime.now(), datetime.now(), datetime.now()],
        "updated_at": [datetime.now(), datetime.now(), datetime.now()]
    })
    
    clean_schema, rejected_schema, schema_metrics = schema_validate(df, "customers")
    clean_business, rejected_business, business_metrics = business_validate(clean_schema, "customers")
    
    # Only phone validation should fail for row 2
    assert len(rejected_business) == 1
    assert "phone_invalid" in business_metrics["checks"]
    assert "phone" in business_metrics["checks"]["phone_invalid"]
    assert business_metrics["checks"]["phone_invalid"]["phone"] == 1


def test_business_rating_range():
    """Test rating range validation"""
    df = pd.DataFrame({
        "restaurant_id": [1, 2, 3, 4],
        "restaurant_name": ["A", "B", "C", "D"],
        "region_id": [1, 1, 1, 1],
        "category_id": [1, 1, 1, 1],
        "price_tier": ["low", "medium", "high", "low"],
        "rating_avg": [5.0, 0.0, 6.0, 4.5],
        "prep_time_avg_min": [30, 25, 35, 28],
        "is_active": [True, True, True, True],
        "created_at": [datetime.now(), datetime.now(), datetime.now(), datetime.now()],
        "updated_at": [datetime.now(), datetime.now(), datetime.now(), datetime.now()]
    })
    
    clean_schema, rejected_schema, schema_metrics = schema_validate(df, "restaurants")
    clean_business, rejected_business, business_metrics = business_validate(clean_schema, "restaurants")
    
    # rating_avg 6.0 should be rejected
    assert len(rejected_business) == 1
    assert "rating_out_of_range" in business_metrics["checks"]
    assert "rating_avg" in business_metrics["checks"]["rating_out_of_range"]
    assert business_metrics["checks"]["rating_out_of_range"]["rating_avg"] == 1
    assert business_metrics["row_in"] == 4


def test_business_negative_amount():
    """Test negative amount validation"""
    df = pd.DataFrame({
        "order_id": ["ORD1", "ORD2", "ORD3"],
        "customer_id": [1, 2, 3],
        "restaurant_id": [1.0, 2.0, 3.0],
        "driver_id": [1, 2, 3],
        "region_id": [1, 1, 1],
        "order_amount": [100.0, -50.0, 75.0],
        "delivery_fee": [5.0, 5.0, 5.0],
        "discount_amount": [10.0, 0.0, 15.0],
        "total_amount": [95.0, -45.0, 65.0],
        "order_status": ["delivered", "delivered", "delivered"],
        "payment_method": ["card", "cash", "card"],
        "order_created_at": [datetime.now(), datetime.now(), datetime.now()],
        "delivered_at": [datetime.now(), datetime.now(), datetime.now()]
    })
    
    clean_schema, rejected_schema, schema_metrics = schema_validate(df, "orders")
    clean_business, rejected_business, business_metrics = business_validate(clean_schema, "orders")
    
    # Row 2 (index 1) has negative order_amount AND negative total_amount
    # So both order_amount and total_amount should be flagged for the same row
    assert len(rejected_business) == 1  # Only one row rejected
    assert "negative_amount" in business_metrics["checks"]
    assert "order_amount" in business_metrics["checks"]["negative_amount"]
    assert business_metrics["checks"]["negative_amount"]["order_amount"] == 1
    assert "total_amount" in business_metrics["checks"]["negative_amount"]
    assert business_metrics["checks"]["negative_amount"]["total_amount"] == 1

def test_business_date_validation():
    """Test date parseability validation"""
    df = pd.DataFrame({
        "customer_id": [1, 2, 3],
        "full_name": ["A", "B", "C"],
        "email": ["a@test.com", "b@test.com", "c@test.com"],
        "phone": ["01157344478", "01157344478", "01157344478"],
        "region_id": [1, 1, 1],
        "segment_id": [1, 1, 1],
        "signup_date": ["2023-01-01", "invalid-date", "n/a"],
        "gender": ["M", "F", "M"],
        "created_at": [datetime.now(), datetime.now(), datetime.now()],
        "updated_at": [datetime.now(), datetime.now(), datetime.now()]
    })
    
    clean_schema, rejected_schema, schema_metrics = schema_validate(df, "customers")
    
    # Schema validator should reject the invalid dates
    assert len(rejected_schema) == 2  # Two rows with invalid dates
    assert len(clean_schema) == 1  # Only first row passes schema validation
    
    # Business validator on clean data should have no date issues
    clean_business, rejected_business, business_metrics = business_validate(clean_schema, "customers")
    assert len(rejected_business) == 0
def test_business_rate_range():
    """Test rate range validation for on_time_rate, cancel_rate"""
    df = pd.DataFrame({
        "driver_id": [1, 2, 3],
        "driver_name": ["Driver A", "Driver B", "Driver C"],
        "driver_phone": ["1234567890", "1234567890", "1234567890"],
        "national_id": ["ID1", "ID2", "ID3"],
        "region_id": [1, 1, 1],
        "shift": ["morning", "evening", "night"],
        "vehicle_type": ["car", "bike", "car"],
        "hire_date": ["2023-01-01", "2023-01-01", "2023-01-01"],
        "rating_avg": [4.5, 4.0, 3.5],
        "on_time_rate": [1.2, 0.5, 1.5],  # 1.2 and 1.5 > 1.0
        "cancel_rate": [-0.1, 0.2, 0.3],  # -0.1 < 0
        "is_active": [True, True, True],
        "created_at": [datetime.now(), datetime.now(), datetime.now()],
        "updated_at": [datetime.now(), datetime.now(), datetime.now()]
    })
    
    clean_schema, rejected_schema, schema_metrics = schema_validate(df, "drivers")
    clean_business, rejected_business, business_metrics = business_validate(clean_schema, "drivers")
    
    assert len(rejected_business) >= 1
    assert "rate_out_of_range" in business_metrics["checks"]


def test_full_pipeline_validation():
    """Test complete validation pipeline with both validators"""
    df = pd.DataFrame({
        "customer_id": [1, 2, 3, 4],
        "full_name": ["John Doe", "Jane Doe", None, "Bob Smith"],
        "email": ["john@test.com", "invalid-email", "jane@test.com", "bob@test.com"],
        "phone": ["01157344478", "01157344478", "01157344478", "01157344478"],
        "region_id": [1, 1, 1, 1],
        "segment_id": [1, 1, 1, 1],
        "signup_date": ["2023-01-01", "2023-01-01", "2023-01-01", "2023-01-01"],
        "gender": ["M", "F", "M", "M"],
        "created_at": [datetime.now()] * 4,
        "updated_at": [datetime.now()] * 4
    })
    
    # Schema validation
    clean_schema, rejected_schema, schema_metrics = schema_validate(df, "customers")
    
    # Schema validation should catch nulls
    assert len(rejected_schema) == 1  # Row with null full_name
    assert len(clean_schema) == 3
    assert schema_metrics["row_in"] == 4
    
    # Business validation on clean data
    clean_business, rejected_business, business_metrics = business_validate(clean_schema, "customers")
    
    # Only email validation should fail for row 2
    assert len(rejected_business) == 1  # Only invalid-email
    assert len(clean_business) == 2  # Rows 1 and 4 pass both validations
    
    # Check rejection reason
    assert "email_invalid" in rejected_business.iloc[0]["rejection_reason"]
    
    # Final clean rows should be John Doe and Bob Smith
    assert clean_business.iloc[0]["full_name"] == "John Doe"
    assert clean_business.iloc[1]["full_name"] == "Bob Smith"
def test_all_schemas_in_registry():
    """Test that all schemas in registry have required fields"""
    for table_name, schema in SCHEMA_REGISTRY.items():
        assert "dtypes" in schema, f"Table {table_name} missing dtypes"
        assert "required_columns" in schema, f"Table {table_name} missing required_columns"
        assert "primary_key" in schema, f"Table {table_name} missing primary_key"
        assert "source_file" in schema, f"Table {table_name} missing source_file"


def test_pii_columns_exist():
    """Test that PII columns are properly marked"""
    pii_tables = ["customers", "drivers", "agents"]
    
    for table_name in pii_tables:
        if table_name in SCHEMA_REGISTRY:
            schema = SCHEMA_REGISTRY[table_name]
            assert "pii_columns" in schema, f"Table {table_name} missing pii_columns"
            assert isinstance(schema["pii_columns"], list), f"Table {table_name} pii_columns not a list"
            
            for col in schema["pii_columns"]:
                assert col in schema["required_columns"], f"PII column {col} not in required_columns for {table_name}"


def test_dwh_columns_exist():
    """Test that DWH-safe columns are properly defined"""
    dwh_tables = ["customers", "drivers", "agents"]
    
    for table_name in dwh_tables:
        if table_name in SCHEMA_REGISTRY:
            schema = SCHEMA_REGISTRY[table_name]
            assert "dwh_columns" in schema, f"Table {table_name} missing dwh_columns"
            assert isinstance(schema["dwh_columns"], list), f"Table {table_name} dwh_columns not a list"
            assert len(schema["dwh_columns"]) > 0, f"Table {table_name} has empty dwh_columns"


def test_foreign_keys_valid():
    """Test that foreign keys reference existing tables"""
    for table_name, schema in SCHEMA_REGISTRY.items():
        if "foreign_keys" in schema:
            for fk_col, ref_table in schema["foreign_keys"].items():
                assert fk_col in schema["dtypes"], f"FK column {fk_col} not in dtypes for {table_name}"
                assert ref_table in SCHEMA_REGISTRY, f"FK references non-existent table {ref_table} from {table_name}"


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "--tb=short"])