# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 StatParity

"""Covariance structure definitions for MMRM models."""

from __future__ import annotations

from enum import Enum, auto


class CovarianceStructure(Enum):
    """Covariance structures for repeated measures models.

    These structures define the assumed correlation pattern across
    repeated measurements within subjects.

    Attributes:
        UNSTRUCTURED: No structure assumed; each variance and covariance
            estimated independently. Most flexible but requires most data.
        COMPOUND_SYMMETRY: Constant correlation between all pairs of
            timepoints. Simplest structure, assumes sphericity.
        AR1: First-order autoregressive. Correlation decreases exponentially
            with time lag. Appropriate for equally spaced visits.
        TOEPLITZ: Banded structure with constant correlation within each
            lag band. Generalizes AR1 to allow different correlations per lag.

    Example:
        >>> from pyrbmi import CovarianceStructure
        >>> CovarianceStructure.UNSTRUCTURED
        <CovarianceStructure.UNSTRUCTURED: 1>
        >>> CovarianceStructure.AR1.name
        'AR1'
    """

    UNSTRUCTURED = auto()
    """Unstructured covariance matrix - no assumptions."""

    COMPOUND_SYMMETRY = auto()
    """Compound symmetry - constant correlation across all timepoints."""

    AR1 = auto()
    """First-order autoregressive - correlation decays with lag."""

    TOEPLITZ = auto()
    """Toeplitz/banded structure - constant correlation per lag band."""

    def __repr__(self) -> str:
        """Return string representation of enum member."""
        return f"CovarianceStructure.{self.name}"
