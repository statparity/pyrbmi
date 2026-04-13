# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 StatParity

"""Imputation strategies for pyrbmi."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class Strategy:
    """Imputation strategy for handling intercurrent events.

    This class defines how missing data is imputed based on the
    ICH E9(R1) estimands framework. Each strategy represents a
    different assumption about post-discontinuation behavior.

    Strategies:
        mar: Missing At Random (standard assumption)
        jump_to_reference: J2R (post-discontinuation follows reference)
        copy_reference: CR (copy reference arm trajectory)
        copy_increment: CIN (copy increment from reference)
        last_mean_carried_forward: LMCF (freeze at last observed)
        treatment_policy: Treatment policy estimand

    Example:
        >>> from pyrbmi import Strategy
        >>> strategy_mar = Strategy.mar()
        >>> strategy_j2r = Strategy.jump_to_reference()
    """

    name: str
    params: dict[str, Any]

    @classmethod
    def mar(cls) -> Strategy:
        """Missing At Random strategy.

        The standard regulatory assumption where discontinuation is
        unrelated to the unobserved outcome. Under MAR, missing values
        are imputed based on observed data patterns.

        Returns:
            A Strategy configured for MAR imputation.
        """
        return cls("mar", {})

    @classmethod
    def jump_to_reference(cls) -> Strategy:
        """Jump to Reference (J2R) strategy.

        After treatment discontinuation, the subject's outcome
        distribution "jumps" to match the reference (typically placebo)
        arm trajectory. Assumes treatment effect is lost after
        discontinuation.

        Returns:
            A Strategy configured for J2R imputation.
        """
        return cls("jump_to_reference", {})

    @classmethod
    def copy_reference(cls) -> Strategy:
        """Copy Reference (CR) strategy.

        The subject's post-baseline outcomes are replaced with draws
        from the reference arm's joint distribution. More extreme
        than J2R — assumes no treatment effect was ever present.

        Returns:
            A Strategy configured for CR imputation.
        """
        return cls("copy_reference", {})

    @classmethod
    def copy_increment(cls) -> Strategy:
        """Copy Increment from Reference (CIN) strategy.

        The subject's post-baseline change from baseline matches the
        reference arm's change from baseline. Subject maintains their
        baseline value but follows reference trajectory.

        Returns:
            A Strategy configured for CIN imputation.
        """
        return cls("copy_increment", {})

    @classmethod
    def last_mean_carried_forward(cls) -> Strategy:
        """Last Mean Carried Forward (LMCF) strategy.

        The subject's mean outcome is frozen at their last observed
        value. Assumes no disease progression after discontinuation
        (optimistic scenario).

        Returns:
            A Strategy configured for LMCF imputation.
        """
        return cls("last_mean_carried_forward", {})

    @classmethod
    def treatment_policy(cls) -> Strategy:
        """Treatment Policy strategy.

        Handles intercurrent events via the treatment policy estimand,
        similar to Intent-to-Treat analysis. Subjects are analyzed
        according to their randomized treatment regardless of what
        actually occurred.

        Returns:
            A Strategy configured for Treatment Policy.
        """
        return cls("treatment_policy", {})
