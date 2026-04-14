# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 StatParity

"""Unit tests for pyrbmi validators."""

from __future__ import annotations

import pandas as pd
import pytest
from pyrbmi.validators import (
    RBMIDataError,
    validate_columns,
    validate_no_duplicate_visits,
    validate_no_missing_baseline,
    validate_reference_arm,
    validate_visit_ordering,
)


class TestValidateColumns:
    """Tests for validate_columns function."""

    def test_happy_path_all_columns_present(self) -> None:
        """Test validation passes when all required columns exist."""
        df = pd.DataFrame({"a": [1, 2], "b": [3, 4], "c": [5, 6]})
        # Should not raise
        validate_columns(df, ["a", "b"])
        validate_columns(df, ["a", "b", "c"])

    def test_error_on_missing_single_column(self) -> None:
        """Test RBMIDataError raised when one column is missing."""
        df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
        with pytest.raises(RBMIDataError, match="Missing required columns"):
            validate_columns(df, ["a", "c"])

    def test_error_on_missing_multiple_columns(self) -> None:
        """Test RBMIDataError lists all missing columns."""
        df = pd.DataFrame({"a": [1, 2]})
        with pytest.raises(RBMIDataError, match="Missing required columns: .*b.*c"):
            validate_columns(df, ["a", "b", "c"])

    def test_error_message_contains_column_names(self) -> None:
        """Test error message includes the missing column names."""
        df = pd.DataFrame({"x": [1, 2]})
        with pytest.raises(RBMIDataError) as exc_info:
            validate_columns(df, ["missing_col"])
        assert "missing_col" in str(exc_info.value)


class TestValidateReferenceArm:
    """Tests for validate_reference_arm function."""

    def test_happy_path_reference_exists(self) -> None:
        """Test validation passes when reference arm exists."""
        df = pd.DataFrame({"treatment": ["Drug", "Placebo", "Drug"]})
        # Should not raise
        validate_reference_arm(df, "treatment", "Placebo")
        validate_reference_arm(df, "treatment", "Drug")

    def test_error_when_reference_not_found(self) -> None:
        """Test RBMIDataError raised when reference arm not in data."""
        df = pd.DataFrame({"treatment": ["Drug", "Placebo"]})
        with pytest.raises(RBMIDataError, match="Reference arm 'Control' not found"):
            validate_reference_arm(df, "treatment", "Control")

    def test_error_message_lists_available_arms(self) -> None:
        """Test error message includes available treatment arms."""
        df = pd.DataFrame({"trt": ["A", "B", "A"]})
        with pytest.raises(RBMIDataError) as exc_info:
            validate_reference_arm(df, "trt", "Z")
        assert "A" in str(exc_info.value)
        assert "B" in str(exc_info.value)


class TestValidateNoDuplicateVisits:
    """Tests for validate_no_duplicate_visits function."""

    def test_happy_path_no_duplicates(self) -> None:
        """Test validation passes with unique (subject, visit) pairs."""
        df = pd.DataFrame(
            {
                "subject": ["S1", "S1", "S2", "S2"],
                "visit": ["V1", "V2", "V1", "V2"],
            }
        )
        # Should not raise
        validate_no_duplicate_visits(df, "subject", "visit")

    def test_error_on_duplicate_subject_visit(self) -> None:
        """Test RBMIDataError raised for duplicate (subject, visit) pairs."""
        df = pd.DataFrame(
            {
                "subject": ["S1", "S1", "S2"],
                "visit": ["V1", "V1", "V1"],  # S1-V1 duplicated
            }
        )
        with pytest.raises(RBMIDataError, match=r"Duplicate \(subject, visit\) combinations"):
            validate_no_duplicate_visits(df, "subject", "visit")

    def test_error_message_shows_examples(self) -> None:
        """Test error message shows example duplicates."""
        df = pd.DataFrame(
            {
                "subj": ["S1", "S1", "S1"],
                "vis": ["V1", "V1", "V2"],  # S1-V1 appears twice
            }
        )
        with pytest.raises(RBMIDataError) as exc_info:
            validate_no_duplicate_visits(df, "subj", "vis")
        # Should mention the duplicate pair
        assert "S1" in str(exc_info.value) or "V1" in str(exc_info.value)

    def test_error_message_shows_total_count(self) -> None:
        """Test error message includes total number of duplicates."""
        df = pd.DataFrame(
            {
                "s": ["S1", "S1", "S2", "S2"],
                "v": ["V1", "V1", "V1", "V1"],  # Two duplicates
            }
        )
        with pytest.raises(RBMIDataError) as exc_info:
            validate_no_duplicate_visits(df, "s", "v")
        assert "Total duplicates: 2" in str(exc_info.value)


class TestValidateVisitOrdering:
    """Tests for validate_visit_ordering function."""

    def test_happy_path_sortable_visits(self) -> None:
        """Test natural sorting for sortable visit values."""
        df = pd.DataFrame({"visit": ["Week 4", "Week 0", "Week 8", "Week 2"]})
        result = validate_visit_ordering(df, "visit")
        assert result == ["Week 0", "Week 2", "Week 4", "Week 8"]

    def test_happy_path_numeric_visits(self) -> None:
        """Test sorting for numeric visit values."""
        df = pd.DataFrame({"visit": [4, 1, 3, 2]})
        result = validate_visit_ordering(df, "visit")
        assert result == [1, 2, 3, 4]

    def test_ordered_categorical_uses_defined_order(self) -> None:
        """Test categorical with ordered=True uses category order."""
        visits = pd.Categorical(
            ["Week 4", "Week 0", "Week 8"],
            categories=["Week 0", "Week 4", "Week 8"],
            ordered=True,
        )
        df = pd.DataFrame({"visit": visits})
        result = validate_visit_ordering(df, "visit")
        assert result == ["Week 0", "Week 4", "Week 8"]

    def test_unordered_categorical_converts_to_sorted(self) -> None:
        """Test categorical without ordering gets sorted."""
        visits = pd.Categorical(["C", "A", "B"])
        df = pd.DataFrame({"visit": visits})
        result = validate_visit_ordering(df, "visit")
        assert result == ["A", "B", "C"]

    def test_unique_visits_only(self) -> None:
        """Test result contains only unique visit values."""
        df = pd.DataFrame({"visit": ["V1", "V1", "V2", "V2", "V3"]})
        result = validate_visit_ordering(df, "visit")
        assert result == ["V1", "V2", "V3"]
        assert len(result) == 3


class TestValidateNoMissingBaseline:
    """Tests for validate_no_missing_baseline function."""

    def test_happy_path_complete_baseline(self) -> None:
        """Test validation passes when all subjects have baseline values."""
        df = pd.DataFrame(
            {
                "subj": ["S1", "S1", "S2", "S2"],
                "base": [10.0, 10.0, 20.0, 20.0],
            }
        )
        # Should not raise
        validate_no_missing_baseline(df, "subj", "base")

    def test_error_when_baseline_missing_for_subject(self) -> None:
        """Test RBMIDataError raised when subject has all NaN baseline."""
        df = pd.DataFrame(
            {
                "subj": ["S1", "S1", "S2", "S2"],
                "base": [None, None, 20.0, 20.0],  # S1 missing baseline
            }
        )
        with pytest.raises(RBMIDataError, match="Missing baseline values for subjects"):
            validate_no_missing_baseline(df, "subj", "base")

    def test_error_message_lists_problematic_subjects(self) -> None:
        """Test error message lists subjects with missing baseline."""
        df = pd.DataFrame(
            {
                "subj": ["S1", "S1", "S2", "S2", "S3", "S3"],
                "base": [None, None, None, None, 30.0, 30.0],  # S1, S2 missing
            }
        )
        with pytest.raises(RBMIDataError) as exc_info:
            validate_no_missing_baseline(df, "subj", "base")
        assert "S1" in str(exc_info.value)
        assert "S2" in str(exc_info.value)


class TestRBMIDatasetIntegration:
    """Integration tests for RBMIDataset validation pipeline."""

    def test_empty_dataframe_raises_error(self) -> None:
        """Test that empty DataFrame raises RBMIDataError."""
        from pyrbmi.data import RBMIDataset

        df = pd.DataFrame()
        with pytest.raises(RBMIDataError, match="DataFrame is empty"):
            RBMIDataset.from_dataframe(
                df,
                subject="subj",
                treatment="trt",
                visit="vis",
                outcome="out",
                reference_arm="A",
            )

    def test_nan_in_critical_column_raises_error(self) -> None:
        """Test that NaN values in critical columns raise RBMIDataError."""
        from pyrbmi.data import RBMIDataset

        df = pd.DataFrame(
            {
                "subj": ["S1", None, "S2"],
                "trt": ["A", "A", "B"],
                "vis": ["V1", "V2", "V1"],
                "out": [1.0, 2.0, 3.0],
            }
        )
        with pytest.raises(RBMIDataError, match="contains NaN values"):
            RBMIDataset.from_dataframe(
                df,
                subject="subj",
                treatment="trt",
                visit="vis",
                outcome="out",
                reference_arm="A",
            )
