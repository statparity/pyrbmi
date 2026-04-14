# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 StatParity

"""Validation utilities for pyrbmi data structures."""

from __future__ import annotations

from typing import Any

import pandas as pd


class RBMIDataError(ValueError):
    """Custom error for RBMI data validation failures."""

    pass


def validate_columns(df: pd.DataFrame, required: list[str]) -> None:
    """Validate that all required columns exist in DataFrame.

    Args:
        df: DataFrame to validate.
        required: List of required column names.

    Raises:
        RBMIDataError: If any required columns are missing.

    Example:
        >>> import pandas as pd
        >>> df = pd.DataFrame({"a": [1], "b": [2]})
        >>> validate_columns(df, ["a", "b"])  # passes
        >>> validate_columns(df, ["a", "c"])  # raises RBMIDataError
    """
    missing = [col for col in required if col not in df.columns]
    if missing:
        msg = f"Missing required columns: {missing}"
        raise RBMIDataError(msg)


def validate_reference_arm(df: pd.DataFrame, treatment_col: str, reference_arm: str) -> None:
    """Validate that reference arm exists in treatment data.

    Args:
        df: DataFrame containing treatment data.
        treatment_col: Name of treatment column.
        reference_arm: Name of reference treatment arm to validate.

    Raises:
        RBMIDataError: If reference arm not found in treatment column.

    Example:
        >>> import pandas as pd
        >>> df = pd.DataFrame({"trt": ["Drug", "Placebo", "Drug"]})
        >>> validate_reference_arm(df, "trt", "Placebo")  # passes
        >>> validate_reference_arm(df, "trt", "Control")  # raises RBMIDataError
    """
    unique_arms = set(df[treatment_col].unique())
    if reference_arm not in unique_arms:
        msg = f"Reference arm '{reference_arm}' not found in {treatment_col}. "
        msg += f"Available arms: {sorted(unique_arms)}"
        raise RBMIDataError(msg)


def validate_no_duplicate_visits(df: pd.DataFrame, subject_col: str, visit_col: str) -> None:
    """Validate no duplicate (subject, visit) combinations exist.

    Args:
        df: DataFrame containing subject and visit columns.
        subject_col: Name of subject identifier column.
        visit_col: Name of visit/timepoint column.

    Raises:
        RBMIDataError: If duplicate (subject, visit) pairs found.

    Example:
        >>> import pandas as pd
        >>> df = pd.DataFrame({
        ...     "subj": ["S1", "S1", "S2"],
        ...     "visit": ["V1", "V2", "V1"]
        ... })
        >>> validate_no_duplicate_visits(df, "subj", "visit")  # passes
        >>> df2 = pd.DataFrame({
        ...     "subj": ["S1", "S1", "S2"],
        ...     "visit": ["V1", "V1", "V1"]  # S1-V1 duplicated
        ... })
        >>> validate_no_duplicate_visits(df2, "subj", "visit")  # raises RBMIDataError
    """
    dupes = df.groupby([subject_col, visit_col]).size()
    dupes = dupes[dupes > 1]

    if not dupes.empty:
        examples = dupes.head(5).index.tolist()
        msg = f"Duplicate (subject, visit) combinations found: {examples}"
        msg += f". Total duplicates: {len(dupes)}"
        raise RBMIDataError(msg)


def validate_visit_ordering(df: pd.DataFrame, visit_col: str) -> list[Any]:
    """Validate and return visit ordering.

    If visit column is categorical with ordered=True, uses that ordering.
    Otherwise, sorts unique visit values naturally.

    Args:
        df: DataFrame containing visit column.
        visit_col: Name of visit column.

    Returns:
        Ordered list of visit values.

    Raises:
        RBMIDataError: If visit column has no valid ordering.

    Example:
        >>> import pandas as pd
        >>> df = pd.DataFrame({"visit": ["Week 4", "Week 0", "Week 8"]})
        >>> validate_visit_ordering(df, "visit")
        ['Week 0', 'Week 4', 'Week 8']
    """
    visit_series = df[visit_col]

    # Check if categorical with ordering
    if pd.api.types.is_categorical_dtype(visit_series):
        if visit_series.cat.ordered:
            return list(visit_series.cat.categories)
        # Categorical but not ordered - convert to sorted unique
        return sorted(visit_series.unique())

    # Try to sort naturally
    try:
        visits = sorted(visit_series.unique())
        return list(visits)
    except TypeError as e:
        msg = f"Cannot determine visit ordering for column '{visit_col}': {e}"
        raise RBMIDataError(msg) from e
