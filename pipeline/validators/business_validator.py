"""
Business Validation Module

Applies business-rule validation on datasets after schema validation

Execution Flow:
1. Step 1: Email format validation
2. Step 2: Phone format validation
3. Step 3: Rating range validation
4. Step 4: Rate range validation 
5. Step 5: Amount range validation (non-negative)
6. Step 6: Date parseability validation

Outputs:
- clean_df: Valid rows ready for downstream processing
- rejected_df: Invalid rows with rejection reasons
- metrics: Validation summary for monitoring and logging

"""

import re
from typing import Any
import pandas as pd
from config import settings as s
import logging

_EMAIL_RE = re.compile(s.EMAIL_REGEX)
_PHONE_RE       = re.compile(s.PHONE_REGEX)
_AGENT_PHONE_RE = re.compile(s.AGENT_PHONE_REGEX)

logger = logging.getLogger(__name__)


def business_validate(df: pd.DataFrame, table_name: str,) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    """
    Apply business validation rules on a DataFrame.

    Args:
        df (pd.DataFrame): Input dataset
        table_name (str): Target table name used to fetch schema

    Returns:
        tuple:
            - clean_df (pd.DataFrame): Valid rows
            - rejected_df (pd.DataFrame): Invalid rows with rejection reasons
            - metrics (dict): Validation statistics

    """

    # Initialize metrics tracking
    metrics: dict[str, Any] = {
        "table_name": table_name,
        "row_in": len(df),
        "rows_rejected": 0,
        "checks": {
            "email_invalid": {},
            "phone_invalid": {},
            "rating_out_of_range": {},
            "rate_out_of_range": {},
            "negative_amount": {},
            "invalid_date": {},
        }
    }

    # Empty dataframe handling
    if df.empty:
        logger.info(f"[BUSINESS] No data to validate - Table: {table_name}")
        return df.copy(), pd.DataFrame(), metrics
    

    # Initialize rejection tracking
    rejected_mask = pd.Series(False, index=df.index)
    rejection_reasons = pd.Series("", index=df.index, dtype="object")

    # Helper function to flag rejected rows
    def _flag(mask: pd.Series, check_type: str, col: str, reason_detail: str = "") -> None:
        """
        Flag rows that failed validation and update metrics 
        Central rejection handler
        
        Args:
            mask: Boolean mask of rows that failed
            check_type: Type of check (e.g., 'email_invalid', 'rating_out_of_range')
            col: Column name that failed validation
            reason_detail: Additional detail for rejection reason (e.g., range values)
        """
        nonlocal rejected_mask, rejection_reasons
        n = int(mask.sum())
        if n > 0:
            # Track failures per column
            metrics["checks"][check_type][col] = n
            
            # standardized rejection reason
            if reason_detail:
                reason = f"{check_type}:{col}({reason_detail})"
            else:
                reason = f"{check_type}:{col}"
            
            # standardized logging
            logger.warning(
                f"{check_type.replace('_', ' ').title()} - Table: {table_name}, "
                f"Column: {col}, Count: {n}"
                + (f", Detail: {reason_detail}" if reason_detail else "")
            )
            
            # Update rejection tracking
            rejected_mask |= mask
            rejection_reasons[mask] += f"{reason}; "




# --------------------------- Step 1: Email Format Validation --------------------------
    email_columns = ["email", "agent_email"]
    for col in email_columns:
        if col in df.columns:
            non_null = df[col].notna()
            if non_null.any():
                invalid = non_null & ~df.loc[non_null, col].apply(
                    lambda v: bool(_EMAIL_RE.match(str(v)))
                )
                _flag(invalid, "email_invalid", col)
    
    
# --------------------------- Step 2: Phone Format Validation --------------------------
    # customers and drivers have leading 0, agents don't
    customer_driver_phones = ["phone", "driver_phone"]
    for col in customer_driver_phones:
        if col in df.columns:
            non_null = df[col].notna()
            if non_null.any():
                invalid = non_null & ~df.loc[non_null, col].apply(
                    lambda v: bool(_PHONE_RE.match(str(v)))
                )
                _flag(invalid, "phone_invalid", col)

    agent_phones = ["agent_phone"]
    for col in agent_phones:
        if col in df.columns:
            non_null = df[col].notna()
            if non_null.any():
                invalid = non_null & ~df.loc[non_null, col].apply(
                    lambda v: bool(_AGENT_PHONE_RE.match(str(v)))
                )
                _flag(invalid, "phone_invalid", col)
    
    # --------------------------- Step 3: Rating Range Validation --------------------------
    rating_columns = ["rating_avg"]
    for col in rating_columns:
        if col in df.columns:
            numeric = pd.to_numeric(df[col], errors="coerce")
            non_null = numeric.notna()
            if non_null.any():
                out_of_range = non_null & (
                    (numeric < s.RATING_MIN) | (numeric > s.RATING_MAX)
                )
                _flag(
                    out_of_range, 
                    "rating_out_of_range", 
                    col,
                    reason_detail=f"{s.RATING_MIN}-{s.RATING_MAX}"
                )
    
    # --------------------------- Step 4: Rate Range Validation --------------------------
    rate_columns = ["on_time_rate", "cancel_rate", "resolution_rate"]
    for col in rate_columns:
        if col in df.columns:
            numeric = pd.to_numeric(df[col], errors="coerce")
            non_null = numeric.notna()
            if non_null.any():
                out_of_range = non_null & (
                    (numeric < s.ON_TIME_RATE_MIN) | (numeric > s.ON_TIME_RATE_MAX)
                )
                _flag(
                    out_of_range,
                    "rate_out_of_range",
                    col,
                    reason_detail=f"{s.ON_TIME_RATE_MIN}-{s.ON_TIME_RATE_MAX}"
                )
    
    # --------------------------- Step 5: Amount Range Validation --------------------------
    amount_columns = ["order_amount", "total_amount", "delivery_fee", "refund_amount", "discount_amount"]
    for col in amount_columns:
        if col in df.columns:
            numeric = pd.to_numeric(df[col], errors="coerce")
            non_null = numeric.notna()
            if non_null.any():
                negative = non_null & (numeric < s.AMOUNT_MIN)
                _flag(negative, "negative_amount", col)
    
    # --------------------------- Step 6: Date Parseability Validation --------------------------
    date_columns = [
        "order_created_at", "delivered_at", "created_at",
        "first_response_at", "resolved_at",
        "sla_first_due_at", "sla_resolve_due_at",
        "event_ts", "signup_date", "hire_date",
    ]
    
    for col in date_columns:
        if col in df.columns:
            non_null = df[col].notna()
            if non_null.any():
                unparseable = non_null & df.loc[non_null, col].apply(_is_bad_date)
                _flag(unparseable, "invalid_date", col)
    
    # --------------------------- Step 7: Split into Clean and Rejected DataFrames --------------------------
    rejected_df = df[rejected_mask].copy()
    clean_df = df[~rejected_mask].copy()
    
    if not rejected_df.empty:
        rejected_df["rejection_reason"] = rejection_reasons[rejected_mask].str.strip().str.rstrip(';')
    
    metrics["rows_rejected"] = len(rejected_df)

    # Log validation summary 
    non_empty_checks = {k: v for k, v in metrics["checks"].items() if v}
    logger.info(
            f"[BUSINESS] Table={table_name} "
            f"In={metrics['row_in']} Clean={len(clean_df)} Rejected={len(rejected_df)} "
            f"Failures={non_empty_checks if non_empty_checks else 'None'}"
    )

    
    return clean_df, rejected_df, metrics


def _is_bad_date(value: Any) -> bool:
    """
    Identify invalid date values.

    Returns:
        True → invalid date
        False → valid or null
    """
    if pd.isna(value):
        return False
    s_val = str(value).strip().lower()
    
    # invalid placeholders
    if s_val in ("", "n/a", "na", "invalid", "none", "null", "unknown", "tbd"):
        return True
    
    try:
        pd.to_datetime(s_val)
        return False
    except Exception:
        return True
