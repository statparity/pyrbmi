# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 StatParity

"""Data structures for pyrbmi."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


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
    baseline_col: str | None
    reference_arm: str

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
        # Stub implementation for documentation
        required_cols = [subject, treatment, visit, outcome]
        missing = [c for c in required_cols if c not in df.columns]
        if missing:
            raise ValueError(f"Missing columns: {missing}")

        return cls(
            df=df.copy(),
            subject_col=subject,
            treatment_col=treatment,
            visit_col=visit,
            outcome_col=outcome,
            baseline_col=baseline,
            reference_arm=reference_arm,
        )
