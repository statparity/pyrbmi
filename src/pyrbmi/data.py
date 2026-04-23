# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 StatParity

"""Data structures for pyrbmi."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from pyrbmi.validators import (
    RBMIDataError,
    validate_columns,
    validate_no_duplicate_visits,
    validate_no_missing_baseline,
    validate_reference_arm,
    validate_visit_ordering,
)


@dataclass
class RBMIDataset:
    """Dataset container for reference-based multiple imputation.

    This class holds longitudinal clinical trial data in ADaM-compatible
    format and prepares it for imputation analysis.

    Attributes:
        df: The source DataFrame containing trial data.
        subject_col: Column name for subject identifier (e.g., 'USUBJID').
        treatment_col: Column name for treatment arm (e.g., 'TRT01A').
        visit_col: Column name for visit/timepoint (e.g., 'AVISIT').
        outcome_col: Column name for outcome variable (e.g., 'AVAL').
        baseline_col: Optional column name for baseline covariate.
        reference_arm: Name of the reference treatment arm.

    Example:
        >>> import pandas as pd
        >>> from pyrbmi import RBMIDataset
        >>> df = pd.DataFrame({
        ...     "USUBJID": ["S1", "S1", "S2", "S2"],
        ...     "TRT01A": ["Drug", "Drug", "Placebo", "Placebo"],
        ...     "AVISIT": ["Week 0", "Week 4", "Week 0", "Week 4"],
        ...     "AVAL": [10.5, 12.3, 11.2, 11.8],
        ... })
        >>> ds = RBMIDataset.from_dataframe(
        ...     df,
        ...     subject="USUBJID",
        ...     treatment="TRT01A",
        ...     visit="AVISIT",
        ...     outcome="AVAL",
        ...     reference_arm="Placebo",
        ... )
    """

    df: pd.DataFrame
    subject_col: str
    treatment_col: str
    visit_col: str
    outcome_col: str
    baseline_col: str | None = None
    reference_arm: str = ""
    _treatment_encoding: dict[str, int] = field(default_factory=dict, repr=False)
    _visit_order: list[Any] = field(default_factory=list, repr=False)

    @classmethod
    def from_dataframe(
        cls,
        df: pd.DataFrame,
        subject: str,
        treatment: str,
        visit: str,
        outcome: str,
        reference_arm: str,
        baseline: str | None = None,
    ) -> RBMIDataset:
        """Create an RBMIDataset from a pandas DataFrame.

        Args:
            df: Source DataFrame in long format.
            subject: Column name for subject identifier.
            treatment: Column name for treatment arm.
            visit: Column name for visit/timepoint.
            outcome: Column name for outcome variable.
            reference_arm: Name of the reference treatment arm.
            baseline: Optional column name for baseline value.

        Returns:
            An RBMIDataset instance configured for imputation analysis.

        Raises:
            ValueError: If required columns are not found in the DataFrame.
        """
        # Validate DataFrame is not empty
        if df.empty:
            raise RBMIDataError("DataFrame is empty")

        # Validate all required columns exist
        required_cols = [subject, treatment, visit, outcome]
        if baseline is not None:
            required_cols.append(baseline)
        validate_columns(df, required_cols)

        # Validate no NaN values in critical columns
        for col in [subject, treatment, visit, outcome]:
            if df[col].isna().any():
                raise RBMIDataError(f"Column '{col}' contains NaN values")
        if baseline is not None and df[baseline].isna().any():
            raise RBMIDataError(f"Baseline column '{baseline}' contains NaN values")

        # Validate reference arm exists in data
        validate_reference_arm(df, treatment, reference_arm)

        # Validate no duplicate (subject, visit) combinations
        validate_no_duplicate_visits(df, subject, visit)

        # Validate and store visit ordering
        visit_order = validate_visit_ordering(df, visit)

        # Create working copy
        df_work = df.copy()

        # Encode treatment arms as integer indices
        treatment_encoding = _encode_treatment_arms(df_work, treatment, reference_arm)

        # Validate baseline completeness if provided
        if baseline is not None:
            validate_no_missing_baseline(df_work, subject, baseline)

        return cls(
            df=df_work,
            subject_col=subject,
            treatment_col=treatment,
            visit_col=visit,
            outcome_col=outcome,
            baseline_col=baseline,
            reference_arm=reference_arm,
            _treatment_encoding=treatment_encoding,
            _visit_order=visit_order,
        )

    def get_treatment_code(self, arm: str) -> int:
        """Get the integer code for a treatment arm.

        Args:
            arm: Treatment arm name.

        Returns:
            Integer code for the arm (reference_arm = 0).

        Raises:
            KeyError: If arm not found in encoding.
        """
        return self._treatment_encoding[arm]

    def get_visit_index(self, visit: Any) -> int:
        """Get the index of a visit in the ordering.

        Args:
            visit: Visit value.

        Returns:
            Index position in visit order.

        Raises:
            ValueError: If visit not found in ordering.
        """
        try:
            return self._visit_order.index(visit)
        except ValueError as e:
            raise ValueError(f"Visit '{visit}' not found in ordering") from e

    def _get_subject_groups(self) -> list[tuple[str, pd.DataFrame]]:
        """Group data by subject for per-subject computations.

        Returns:
            List of (subject_id, subject_df) tuples.
            Each subject_df contains rows for that subject with visits in canonical order.
        """
        # Sort by subject and visit order to ensure canonical ordering
        df_sorted = self.df.sort_values(
            by=[self.subject_col, self.visit_col],
            key=lambda col: col.map(self._visit_order.index) if col.name == self.visit_col else col,
        )
        return list(df_sorted.groupby(self.subject_col, sort=False))


def _encode_treatment_arms(
    df: pd.DataFrame,
    treatment_col: str,
    reference_arm: str,
) -> dict[str, int]:
    """Encode treatment arms as integer indices.

    The reference arm is always encoded as 0.
    Other arms are encoded as 1, 2, 3, ... in sorted order.

    Args:
        df: DataFrame with treatment column.
        treatment_col: Name of treatment column.
        reference_arm: Name of reference treatment arm.

    Returns:
        Dictionary mapping arm names to integer codes.
    """
    unique_arms = sorted(df[treatment_col].unique())

    # Note: reference_arm validation already done in validate_reference_arm()

    # Build encoding: reference = 0, others sorted = 1, 2, 3, ...
    encoding: dict[str, int] = {reference_arm: 0}
    code = 1
    for arm in unique_arms:
        if arm != reference_arm:
            encoding[arm] = code
            code += 1

    # Add encoded column to dataframe using unique internal name
    internal_col = f"_pyrbmi_treatment_code_{treatment_col}"
    if internal_col in df.columns:
        raise RBMIDataError(
            f"Reserved internal column name '{internal_col}' already exists in DataFrame"
        )
    df[internal_col] = df[treatment_col].map(encoding)

    return encoding
