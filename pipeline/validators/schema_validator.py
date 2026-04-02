"""
Schema Validation Module

Performs row-level and schema-level validation for incoming datasets

Execution Flow:
1. step 1: Required Columns Check -> Reject entire dataset if missing columns
2. step 2: Nullability Check -> Reject rows with nulls in required columns
3. step 3: Primary Key Deduplication -> Keep first occurrence, reject duplicates
4. step 4: Data Type Validation -> Reject rows with invalid data types

Outputs:
- clean_df: Valid rows ready for downstream processing
- rejected_df: Invalid rows with rejection reasons
- metrics: Validation summary for monitoring and logging

"""

import logging
from typing import Any
import pandas as pd
from config.schemas import SCHEMA_REGISTRY, INT, FLT, BOOL, DATE, DT, STR

logger = logging.getLogger(__name__)

def schema_validate(df:pd.DataFrame, table_name: str)->tuple[pd.DataFrame, pd.DataFrame,dict[str, Any]]:
    """
    Validate a DataFrame against a predefined schema.

    Args:
        df (pd.DataFrame): Input dataset
        table_name (str): Target table name used to fetch schema

    Returns:
        tuple:
            - clean_df (pd.DataFrame): Valid rows
            - rejected_df (pd.DataFrame): Invalid rows with rejection reasons
            - metrics (dict): Validation statistics

    Behavior:
        - Rejects entire dataset if schema is missing or invalid
        - Applies row-level validation for nulls, duplicates, and dtype issues
        - Tracks detailed metrics for observability
    """

    schema = SCHEMA_REGISTRY.get(table_name, {})
    dtypes = schema.get("dtypes", {})

    # --------------------------- Schema existence check ---------------------------

    if not schema:
        logger.error(f"[SCHEMA] No schema found for table: {table_name}")
        metrics = {
            "table_name": table_name,
            "missing_columns": [],
            "null_counts": {},
            "duplicate_counts": 0,
            "row_in": len(df),
            "rows_rejected": len(df),
            "dtype_fails": {},
        }
        rejected_df = df.copy()
        rejected_df["rejection_reason"] = f"Schema not found: {table_name}"
        # Return empty clean dataframe cause all rows rejected
        return pd.DataFrame(columns=df.columns), rejected_df, metrics

    required_columns: list[str] = schema.get("required_columns", [])
    pk_col: str |None = schema.get("primary_key")
    metrics : dict[str, Any] = {
        "table_name" : table_name,
        "missing_columns": [],
        "null_counts": {},
        "duplicate_counts": {},
        "row_in": len(df),
        "rows_rejected": 0,
        "dtype_fails": {},  # {col: count_of_bad_values}
    }

    # empty df, nothing to validate, return empty clean and rejected dfs
    if df.empty:
        return df.copy(), pd.DataFrame(), metrics
    

    # --------------------------- Step 1: checking required columns----------------------------
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        logger.error(f"[SCHEMA] Missing required columns - Table: {table_name}, Columns: {missing_columns}")

        metrics["missing_columns"] = missing_columns
        rejected_df = df.copy()
        rejected_df["rejection_reason"] = (f"Missing required columns: {', '.join(missing_columns)}")
        metrics["rows_rejected"] = len(rejected_df)
        
        # reject all data cause of schema failure
        return pd.DataFrame(columns=df.columns), rejected_df, metrics
    

    # Initialize rejection tracking
    rejected_mask = pd.Series(False, index=df.index)
    rejection_reasons = pd.Series("", index=df.index, dtype="object")

    # --------------------------- Step 2: checking nulls -----------------------
    # required column exists but contains null rows -> reject them
    for col in required_columns:
        null_mask = df[col].isnull()
        null_count = null_mask.sum()
        metrics["null_counts"][col] = int(null_count)

        if null_count > 0:
            logger.info(f"[NULL] Table: {table_name}, Column: {col}, Count: {null_count}")
            
            # marking the null rows with true in rejected mask
            rejected_mask |= null_mask
            rejection_reasons[null_mask] += f"Null: {col}; " #reason per row, + if it had other reasons in the comming checks
   
    # --------------------------- Step 3: checking PK dublicates -----------------------
    # keep the first pk and reject the rest 
    dup_count = 0
    if pk_col and pk_col in df.columns:
        # true -> dublicate and the first one is false
        dup_mask = df.duplicated(subset=[pk_col], keep="first")
        dup_count = int(dup_mask.sum())
        metrics["duplicate_counts"] = dup_count

        if dup_count > 0:
            logger.info(f"[DUPLICATE] Table: {table_name}, PK: {pk_col}, Count: {dup_count}")
            
            # add them to the previous rejected rows
            rejected_mask |= dup_mask
            rejection_reasons.loc[dup_mask] += f"duplicate:{pk_col}"

 # --------------------------- Step 4: Dtype Validation -----------------------
 #  dtype validation only on rows that haven't been rejected yet
    if dtypes and not df.empty:
        # Only check rows that are currently clean 
        clean_mask = ~rejected_mask
        if clean_mask.any():
            # Apply dtype validation to clean rows
            for col, expected_dtype in dtypes.items():
                if col not in df.columns:
                    continue
                if expected_dtype == STR:
                    continue 

                # Get the series for clean rows only
                clean_series = df.loc[clean_mask, col]
                bad_mask_in_clean = _find_bad_values(clean_series, expected_dtype)
                
                if bad_mask_in_clean.any():
                    # Convert the boolean mask from clean rows back to full dataframe index
                    full_bad_mask = pd.Series(False, index=df.index)
                    full_bad_mask[clean_mask] = bad_mask_in_clean
                    
                    count = int(bad_mask_in_clean.sum())
                    metrics["dtype_fails"][col] = count
                    
                    logger.info(f"[DTYPE] Table: {table_name}, Column: {col}, "
                        f"Expected: {expected_dtype}, Count: {count}")
                    
                    rejected_mask |= full_bad_mask
                    rejection_reasons[full_bad_mask] += f"dtype_fail:{col}({expected_dtype});"

    # --------------------------- Step 5: split into clean and rejected rows -----------------------

    rejected_df = df[rejected_mask].copy()
    clean_df = df[~rejected_mask].copy()

    if not rejected_df.empty:
        rejected_df["rejection_reason"] = rejection_reasons[rejected_mask].str.strip()

    metrics["rows_rejected"] = len(rejected_df)

    logger.info(
        f"[VALIDATION] Table: {table_name} | "
        f"In={metrics['row_in']} Clean={len(clean_df)} Rejected={len(rejected_df)} | "
        f"Duplicates={metrics['duplicate_counts']} "
        f"DtypeFails={metrics['dtype_fails']}"
    )

    return clean_df, rejected_df, metrics

def _find_bad_values(series: pd.Series, dtype: str) -> pd.Series:
    """
    Identify values that cannot be cast to the expected dtype.

    Args:
        series (pd.Series): Input column
        dtype (str): Expected data type

    Returns:
        pd.Series: Boolean mask (True = invalid value)
    
    """
    not_null = series.notna()

    if dtype in (INT, FLT):
        numeric = pd.to_numeric(series, errors="coerce")
        return not_null & numeric.isna()

    if dtype == BOOL:
        valid_vals = {"true", "false", "1", "0", "yes", "no"}
        return not_null & ~series.astype(str).str.lower().isin(valid_vals)

    if dtype in (DATE, DT):
        parsed = pd.to_datetime(series, errors="coerce")
        return not_null & parsed.isna()

    # Unknown dtype —> skip
    return pd.Series(False, index=series.index)