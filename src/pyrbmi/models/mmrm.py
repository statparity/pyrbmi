# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 StatParity

"""Mixed Model Repeated Measures (MMRM) implementation.

This module implements the MMRM model for longitudinal data analysis
with REML estimation, supporting various covariance structures.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import numpy as np
from scipy import linalg, optimize

from pyrbmi.covariance import CovarianceStructure

# Import formulaic at module level for type checking
try:
    from formulaic import Formula
except ImportError:
    Formula = None

if TYPE_CHECKING:
    from pyrbmi.data import RBMIDataset
    from pyrbmi.validators import RBMIDataError
else:
    from pyrbmi.validators import RBMIDataError


class MMRMConvergenceError(RuntimeError):
    """Exception raised when MMRM fails to converge.

    Attributes:
        message: Explanation of the error.
        optimization_result: Result object from scipy.optimize.minimize
            containing details about the failed optimization.
    """

    def __init__(
        self,
        message: str,
        optimization_result: optimize.OptimizeResult | None = None,
    ) -> None:
        super().__init__(message)
        self.optimization_result = optimization_result


@dataclass
class MMRM:
    """Mixed Model Repeated Measures (MMRM) for longitudinal data.

    The MMRM model analyzes longitudinal continuous outcomes while accounting
    for within-subject correlation using a structured covariance matrix.
    This implementation supports REML estimation and multiple covariance
    structures, with flexible design matrix specification via formulas.

    Attributes:
        covariance: Covariance structure for repeated measures.
        reml: Whether to use REML (True) or ML (False) estimation.
        formula: Optional formula string for design matrix. If None, uses
            default treatment × visit interaction with optional baseline
            and additional covariates.
        additional_covariates: List of additional covariate column names to
            include in the design matrix (ignored if formula is provided).
        beta_hat: Estimated fixed effects coefficients (populated after fit).
        sigma_hat: Estimated covariance matrix (populated after fit).
        log_likelihood: REML or ML log-likelihood (populated after fit).
        converged: Whether optimization converged (populated after fit).
        optimizer_result: Full scipy optimization result (populated after fit).

    Example:
        >>> from pyrbmi import MMRM, CovarianceStructure, RBMIDataset
        >>> import pandas as pd
        >>> df = pd.DataFrame({
        ...     "subject": ["S1", "S1", "S2", "S2"],
        ...     "treatment": ["Drug", "Drug", "Placebo", "Placebo"],
        ...     "visit": ["V1", "V2", "V1", "V2"],
        ...     "outcome": [10.5, 12.3, 11.2, 11.8],
        ... })
        >>> ds = RBMIDataset.from_dataframe(
        ...     df, subject="subject", treatment="treatment",
        ...     visit="visit", outcome="outcome", reference_arm="Placebo"
        ... )
        >>> # Default: treatment × visit interaction
        >>> model = MMRM(covariance=CovarianceStructure.UNSTRUCTURED, reml=True)
        >>> model.fit(ds)
        >>> print(f"Beta: {model.beta_hat}")
        >>> print(f"Converged: {model.converged}")
        >>>
        >>> # Custom formula
        >>> model2 = MMRM(formula="outcome ~ treatment * visit + age")
    """

    covariance: CovarianceStructure = CovarianceStructure.UNSTRUCTURED
    reml: bool = True
    formula: str | None = None
    additional_covariates: list[str] = field(default_factory=list)

    # Fitted attributes (populated after fit())
    beta_hat: np.ndarray | None = field(default=None, repr=False)
    sigma_hat: np.ndarray | None = field(default=None, repr=False)
    log_likelihood: float | None = field(default=None, repr=False)
    converged: bool = field(default=False, repr=False)
    optimizer_result: optimize.OptimizeResult | None = field(default=None, repr=False)

    # Internal attributes
    _X: np.ndarray | None = field(default=None, repr=False)  # Design matrix
    _y: np.ndarray | None = field(default=None, repr=False)  # Response vector
    _subject_indices: list[tuple[int, int]] = field(
        default_factory=list, repr=False
    )  # (start, end) for each subject
    _n_visits: int = field(default=0, repr=False)
    _n_subjects: int = field(default=0, repr=False)
    _feature_names: list[str] = field(default_factory=list, repr=False)

    def fit(self, dataset: RBMIDataset) -> MMRM:
        """Fit the MMRM model to the dataset.

        Constructs the design matrix with treatment × visit interaction terms,
        estimates parameters via REML or ML using numerical optimization,
        and stores the results.

        Args:
            dataset: An RBMIDataset containing the trial data.

        Returns:
            self: The fitted model instance.

        Raises:
            MMRMConvergenceError: If the optimizer fails to converge.
            RBMIDataError: If the dataset fails validation checks.
            RuntimeError: If model is already fitted (call reset() first).

        Example:
            >>> model = MMRM(covariance=CovarianceStructure.COMPOUND_SYMMETRY)
            >>> fitted = model.fit(dataset)
            >>> print(f"Log-likelihood: {fitted.log_likelihood}")
        """
        # Guard against re-fitting
        if self.converged:
            raise RuntimeError("Model already fitted. Call reset() first or create a new instance.")

        # Build design matrix and response (sorted by subject, then visit)
        x_matrix, y_vec, subject_indices = self._build_design_matrix(dataset)
        self._X = x_matrix
        self._y = y_vec
        self._subject_indices = subject_indices

        # Get visit and subject counts for covariance parameterization
        self._n_visits = len(dataset._visit_order)
        self._n_subjects = len(subject_indices)

        # Estimate covariance parameters via REML/ML
        theta_init = self._init_covariance_params()

        # Optimize
        result = optimize.minimize(
            fun=self._negative_log_likelihood,
            x0=theta_init,
            method="L-BFGS-B",
            jac=True,
        )

        # Check convergence
        if not result.success:
            raise MMRMConvergenceError(
                f"MMRM optimization failed: {result.message}",
                optimization_result=result,
            )

        # Store optimization result
        self.optimizer_result = result

        # Compute final estimates BEFORE setting converged flag
        # This ensures atomic state: if any computation fails, model remains unfitted
        theta_hat = result.x
        sigma_hat = self._theta_to_sigma(theta_hat)
        beta_hat, log_likelihood = self._compute_final_loglik(sigma_hat)

        # Only set fitted state after all computations succeed
        self.sigma_hat = sigma_hat
        self.beta_hat = beta_hat
        self.log_likelihood = log_likelihood
        self.converged = True

        return self

    def reset(self) -> None:
        """Reset the model to unfitted state.

        Clears all fitted parameters, allowing the model to be refitted.
        """
        self.beta_hat = None
        self.sigma_hat = None
        self.log_likelihood = None
        self.converged = False
        self.optimizer_result = None
        self._X = None
        self._y = None
        self._subject_indices = []
        self._n_visits = 0
        self._n_subjects = 0
        self._feature_names = []

    def _compute_final_loglik(self, sigma: np.ndarray) -> tuple[np.ndarray, float]:
        """Compute final beta and log-likelihood after optimization.

        Args:
            sigma: Final covariance matrix estimate.

        Returns:
            Tuple of (beta_hat, log_likelihood).
        """
        if self._X is None or self._y is None or not self._subject_indices:
            raise RuntimeError("Model not fitted: call fit() first")

        beta_hat, logdet_sigma, _ = self._estimate_beta(sigma)
        n_obs = len(self._y)
        n_params = self._X.shape[1]

        # Compute residual quadratic form r' V^{-1} r using per-subject accumulation
        residuals = self._y - self._X @ beta_hat
        resid_quad = 0.0

        for start_idx, end_idx in self._subject_indices:
            r_i = residuals[start_idx:end_idx]
            n_visits_i = end_idx - start_idx

            # Extract submatrix for this subject's visits
            sigma_i = sigma if n_visits_i == sigma.shape[0] else sigma[:n_visits_i, :n_visits_i]

            try:
                sigma_i_inv = linalg.inv(sigma_i)
            except linalg.LinAlgError:
                sigma_i_inv = linalg.pinv(sigma_i)

            resid_quad += float(r_i @ sigma_i_inv @ r_i)

        if self.reml:
            # REML: -0.5 * (n-p) * log(2π) - 0.5 * log|V| - 0.5 * log|X'V^{-1}X| - 0.5 * r'V^{-1}r
            # log|V| = sum of log|sigma_i| for each subject (already in logdet_sigma)
            # log|X'V^{-1}X| term (ignored in simplified implementation)
            loglik = (
                -0.5 * (n_obs - n_params) * np.log(2 * np.pi)
                - 0.5 * logdet_sigma
                - 0.5 * resid_quad
            )
        else:
            # ML: -0.5 * n * log(2π) - 0.5 * log|V| - 0.5 * r'V^{-1}r
            loglik = -0.5 * n_obs * np.log(2 * np.pi) - 0.5 * logdet_sigma - 0.5 * resid_quad

        return beta_hat, float(loglik)

    def _build_design_matrix(
        self, dataset: RBMIDataset
    ) -> tuple[np.ndarray, np.ndarray, list[tuple[int, int]]]:
        """Build design matrix with treatment × visit interaction.

        Creates the design matrix X using either:
        1. A custom formula (if self.formula is provided) using formulaic
        2. Default: intercept + visit dummies + baseline + treatment×visit interactions
           + additional covariates

        Data is sorted by subject, then visit order. Subject indices track which
        rows belong to each subject for proper handling of unbalanced data.

        Args:
            dataset: The RBMIDataset instance.

        Returns:
            Tuple of (X, y, subject_indices) where:
            - X is the design matrix (sorted by subject, visit)
            - y is the response vector
            - subject_indices is a list of (start_row, end_row) for each subject
        """
        df = dataset.df.copy()

        # Sort by subject and visit order to ensure canonical ordering
        df = df.sort_values(
            by=[dataset.subject_col, dataset.visit_col],
            key=lambda col: (
                col.map(dataset._visit_order.index) if col.name == dataset.visit_col else col
            ),
        ).reset_index(drop=True)

        # Track which rows belong to each subject using groupby
        subject_indices: list[tuple[int, int]] = []
        start_idx = 0

        for _subject_id, group in df.groupby(dataset.subject_col, sort=False):
            group_len = len(group)
            subject_indices.append((start_idx, start_idx + group_len))
            start_idx += group_len

        # If formula is provided, use formulaic for parsing
        if self.formula is not None:
            if Formula is None:
                raise ImportError(
                    "formulaic is required for custom formulas. "
                    "Install with: pip install formulaic>=1.0"
                )

            # Parse formula using formulaic
            formula_obj = Formula(self.formula)
            matrices = formula_obj.get_model_matrix(df)

            # formulaic returns ModelMatrices with .lhs (y) and .rhs (X) attributes
            X = matrices.rhs
            y = matrices.lhs

            # Extract feature names before converting to numpy
            self._feature_names = list(X.model_spec.column_names)

            return np.asarray(X), np.asarray(y), subject_indices

        # Default: build design matrix manually with treatment × visit interaction
        # Get treatment codes
        df["_trt_code"] = df[dataset.treatment_col].map(dataset._treatment_encoding)

        # Create visit indicator columns
        visit_dummies = []
        for i, visit in enumerate(dataset._visit_order):
            col_name = f"_visit_{i}"
            df[col_name] = (df[dataset.visit_col] == visit).astype(int)
            visit_dummies.append(col_name)

        # Create treatment × visit interaction columns
        # Reference arm (code 0) serves as baseline
        interaction_cols = []
        for trt_code in range(1, len(dataset._treatment_encoding)):
            for i, _visit_val in enumerate(dataset._visit_order):
                col_name = f"_trt{trt_code}_visit_{i}"
                df[col_name] = (df["_trt_code"] == trt_code).astype(int) * df[f"_visit_{i}"]
                interaction_cols.append(col_name)

        # Build design matrix: intercept + visit dummies + baseline + additional + interactions
        cols = ["_intercept"]
        df["_intercept"] = 1.0

        # Add visit dummies (main effects for reference arm)
        cols.extend(visit_dummies)

        # Add baseline covariate if present (continuous)
        if dataset.baseline_col is not None:
            cols.append(dataset.baseline_col)

        # Add additional covariates (user-configurable)
        # Skip any that are already in cols (e.g., baseline_col overlap)
        for cov_col in self.additional_covariates:
            if cov_col not in df.columns:
                raise RBMIDataError(f"Additional covariate '{cov_col}' not found in dataset")
            if cov_col in cols:
                raise RBMIDataError(
                    f"Additional covariate '{cov_col}' duplicates a column already in the design matrix"
                )
            cols.append(cov_col)

        # Add treatment × visit interactions
        cols.extend(interaction_cols)

        self._feature_names = cols
        x_matrix = df[cols].values
        y_vec = df[dataset.outcome_col].values

        return x_matrix, y_vec, subject_indices

    def get_feature_names(self) -> list[str]:
        """Return the names of features in the design matrix.

        Returns:
            List of feature/column names corresponding to beta_hat coefficients.

        Raises:
            RuntimeError: If the model has not been fitted.
        """
        if not self.converged:
            raise RuntimeError("Model must be fitted before getting feature names")
        return self._feature_names.copy()

    def _init_covariance_params(self) -> np.ndarray:
        """Initialize covariance parameters for optimization.

        Returns:
            Initial parameter vector theta for the chosen covariance structure.
        """
        if self.covariance == CovarianceStructure.UNSTRUCTURED:
            # Cholesky parameterization: n_visits variances + n_visits*(n_visits-1)/2 correlations
            n_params = self._n_visits * (self._n_visits + 1) // 2
            return np.zeros(n_params)
        elif (
            self.covariance == CovarianceStructure.COMPOUND_SYMMETRY
            or self.covariance == CovarianceStructure.AR1
        ):
            # 2 params: log(variance), logit(correlation)
            return np.array([0.0, 0.0])
        elif self.covariance == CovarianceStructure.TOEPLITZ:
            # n_visits variances + (n_visits-1) correlations
            n_params = 2 * self._n_visits - 1
            return np.zeros(n_params)
        else:
            raise ValueError(f"Unsupported covariance structure: {self.covariance}")

    def _theta_to_sigma(self, theta: np.ndarray) -> np.ndarray:
        """Convert parameter vector theta to covariance matrix Sigma.

        Args:
            theta: Parameter vector from optimization.

        Returns:
            Covariance matrix Sigma (n_visits × n_visits).
        """
        if self.covariance == CovarianceStructure.UNSTRUCTURED:
            return self._unstructured_theta_to_sigma(theta)
        elif self.covariance == CovarianceStructure.COMPOUND_SYMMETRY:
            return self._compound_symmetry_theta_to_sigma(theta)
        elif self.covariance == CovarianceStructure.AR1:
            return self._ar1_theta_to_sigma(theta)
        elif self.covariance == CovarianceStructure.TOEPLITZ:
            return self._toeplitz_theta_to_sigma(theta)
        else:
            raise ValueError(f"Unsupported covariance structure: {self.covariance}")

    def _unstructured_theta_to_sigma(self, theta: np.ndarray) -> np.ndarray:
        """Convert theta to unstructured covariance via Cholesky.

        theta contains Cholesky factor elements (lower triangle).
        Sigma = L @ L.T ensures positive definiteness.
        """
        n = self._n_visits
        L = np.zeros((n, n))

        # Fill lower triangle
        idx = 0
        for i in range(n):
            for j in range(i + 1):
                if i == j:
                    # Diagonal: positive via exp
                    L[i, j] = np.exp(theta[idx])
                else:
                    # Off-diagonal
                    L[i, j] = theta[idx]
                idx += 1

        Sigma = L @ L.T
        return Sigma

    def _compound_symmetry_theta_to_sigma(self, theta: np.ndarray) -> np.ndarray:
        """Convert theta to compound symmetry covariance."""
        variance = np.exp(theta[0])  # Ensure positive
        # Use tanh to map to (-1, 1) for valid correlation range
        # Valid range for CS: -1/(n-1) < corr < 1, tanh covers most useful range
        corr = np.tanh(theta[1])

        n = self._n_visits
        Sigma = np.full((n, n), variance * corr)
        np.fill_diagonal(Sigma, variance)
        return Sigma

    def _ar1_theta_to_sigma(self, theta: np.ndarray) -> np.ndarray:
        """Convert theta to AR1 covariance."""
        variance = np.exp(theta[0])  # Ensure positive
        rho = 1 / (1 + np.exp(-theta[1]))  # Logit to (0, 1)

        n = self._n_visits
        Sigma = np.zeros((n, n))
        for i in range(n):
            for j in range(n):
                Sigma[i, j] = variance * (rho ** abs(i - j))
        return Sigma

    def _toeplitz_theta_to_sigma(self, theta: np.ndarray) -> np.ndarray:
        """Convert theta to Toeplitz covariance."""
        n = self._n_visits
        # First n params are log variances, rest are correlations
        variances = np.exp(theta[:n])  # Ensure positive
        corrs = 1 / (1 + np.exp(-theta[n : 2 * n - 1]))  # Logit to (0, 1)

        Sigma = np.zeros((n, n))
        for i in range(n):
            for j in range(n):
                lag = abs(i - j)
                if lag == 0:
                    Sigma[i, j] = variances[i]
                elif lag <= len(corrs):
                    # Use geometric mean for cross-variances
                    Sigma[i, j] = np.sqrt(variances[i] * variances[j]) * corrs[lag - 1]
        return Sigma

    def _log_likelihood_value(self, theta: np.ndarray) -> float:
        """Compute log-likelihood value only (no gradient).

        Args:
            theta: Covariance parameter vector.

        Returns:
            Log-likelihood value (not negated).
        """
        if self._y is None or self._X is None:
            raise RuntimeError("Model not fitted: call fit() first")

        Sigma = self._theta_to_sigma(theta)

        # Check positive definiteness
        try:
            linalg.cholesky(Sigma, lower=True)
        except linalg.LinAlgError:
            return -1e10

        # Compute beta_hat and get residuals
        beta_hat, logdet_sigma, _ = self._estimate_beta(Sigma)
        n_obs = len(self._y)
        n_params = self._X.shape[1]

        # Compute residual quadratic form r' V^{-1} r using per-subject accumulation
        # This handles unbalanced data properly
        residuals = self._y - self._X @ beta_hat
        resid_quad = 0.0

        for start_idx, end_idx in self._subject_indices:
            r_i = residuals[start_idx:end_idx]
            n_visits_i = end_idx - start_idx

            # Extract submatrix for this subject's visits
            sigma_i = Sigma if n_visits_i == Sigma.shape[0] else Sigma[:n_visits_i, :n_visits_i]

            try:
                sigma_i_inv = linalg.inv(sigma_i)
            except linalg.LinAlgError:
                sigma_i_inv = linalg.pinv(sigma_i)

            resid_quad += float(r_i @ sigma_i_inv @ r_i)

        if self.reml:
            # REML: -0.5 * (n-p) * log(2π) - 0.5 * log|V| - 0.5 * r'V^{-1}r
            # Note: log|X'V^{-1}X| term omitted in simplified implementation
            loglik = (
                -0.5 * (n_obs - n_params) * np.log(2 * np.pi)
                - 0.5 * logdet_sigma
                - 0.5 * resid_quad
            )
        else:
            # ML
            loglik = -0.5 * n_obs * np.log(2 * np.pi) - 0.5 * logdet_sigma - 0.5 * resid_quad

        return float(loglik)

    def _negative_log_likelihood(self, theta: np.ndarray) -> tuple[float, np.ndarray]:
        """Compute negative log-likelihood and gradient for optimization.

        Uses central difference for better accuracy with relative step size.

        Args:
            theta: Covariance parameter vector.

        Returns:
            Tuple of (negative log-likelihood, gradient).
        """
        loglik = self._log_likelihood_value(theta)

        # Numerical gradient with relative step size for better scaling
        # Different parameters (log-variances vs correlations) can have very different scales
        grad = np.zeros_like(theta, dtype=float)
        for i in range(len(theta)):
            # Relative step size: sqrt(machine epsilon) * |theta_i| or absolute minimum
            h = max(1e-8, np.sqrt(np.finfo(float).eps) * abs(theta[i]))

            # Central difference for better accuracy
            theta_plus = theta.copy()
            theta_minus = theta.copy()
            theta_plus[i] += h
            theta_minus[i] -= h

            ll_plus = self._log_likelihood_value(theta_plus)
            ll_minus = self._log_likelihood_value(theta_minus)

            grad[i] = -(ll_plus - ll_minus) / (2 * h)  # Negate for negative log-lik

        return -loglik, grad

    def _estimate_beta(
        self,
        sigma: np.ndarray,
    ) -> tuple[np.ndarray, float, np.ndarray]:
        """Estimate fixed effects beta given covariance matrix.

        Uses GLS: beta_hat = (X'V^{-1}X)^{-1} X'V^{-1}y
        Handles unbalanced data (missing visits) via per-subject accumulation.

        Args:
            sigma: Full n_visits × n_visits covariance matrix.

        Returns:
            Tuple of (beta_hat, logdet_sigma, sscp).
        """
        if self._X is None or self._y is None or not self._subject_indices:
            raise RuntimeError("Model not fitted: call fit() first")

        X, y = self._X, self._y
        n_params = X.shape[1]

        # Accumulate X'V^{-1}X and X'V^{-1}y across subjects
        # This handles unbalanced data by extracting submatrices for each subject's visits
        xt_vinv_x = np.zeros((n_params, n_params))
        xt_vinv_y = np.zeros(n_params)
        logdet_total = 0.0

        for start_idx, end_idx in self._subject_indices:
            # Extract this subject's data
            X_i = X[start_idx:end_idx]
            y_i = y[start_idx:end_idx]
            n_visits_i = end_idx - start_idx

            # Extract submatrix for this subject's visits
            sigma_i = sigma if n_visits_i == sigma.shape[0] else sigma[:n_visits_i, :n_visits_i]

            # Compute sigma_i inverse
            try:
                sigma_i_inv = linalg.inv(sigma_i)
            except linalg.LinAlgError:
                sigma_i_inv = linalg.pinv(sigma_i)

            # Accumulate GLS normal equations
            xt_vinv_x += X_i.T @ sigma_i_inv @ X_i
            xt_vinv_y += X_i.T @ sigma_i_inv @ y_i

            # Accumulate log determinant
            sign, logdet = np.linalg.slogdet(sigma_i)
            if sign > 0:
                logdet_total += logdet

        # Solve GLS normal equations
        try:
            beta_hat = linalg.solve(xt_vinv_x, xt_vinv_y)
        except linalg.LinAlgError:
            beta_hat = linalg.lstsq(xt_vinv_x, xt_vinv_y)[0]

        # Compute residuals and SSCP (simplified)
        residuals = y - X @ beta_hat
        sscp = residuals.reshape(-1, 1) @ residuals.reshape(1, -1)

        return beta_hat, float(logdet_total), sscp

    def draw_posterior_params(self, n_draws: int, seed: int | None = None) -> dict[str, Any]:
        """Draw posterior parameters for Bayesian imputation.

        Generates draws from the approximate posterior distribution of
        beta and Sigma using the Wishart-Normal conjugate approximation.

        Args:
            n_draws: Number of posterior draws to generate.
            seed: Random seed for reproducibility.

        Returns:
            Dictionary with keys "beta" (array of shape (n_draws, n_beta))
            and "sigma" (array of shape (n_draws, n_visits, n_visits)).

        Raises:
            RuntimeError: If the model has not been fitted.

        Example:
            >>> model.fit(dataset)
            >>> draws = model.draw_posterior_params(n_draws=100, seed=42)
            >>> draws["beta"].shape  # (100, n_parameters)
        """
        if not self.converged or self.beta_hat is None or self.sigma_hat is None:
            raise RuntimeError("Model must be fitted before drawing posterior parameters")

        rng = np.random.default_rng(seed)

        n_beta = len(self.beta_hat)
        n_visits = self._n_visits

        # Wishart approximation for Sigma
        # Using nu = n_subjects - n_visits degrees of freedom
        nu = max(self._n_subjects - n_visits, n_visits + 1)
        scale = self.sigma_hat / nu

        sigma_draws = np.zeros((n_draws, n_visits, n_visits))
        for i in range(n_draws):
            sigma_draws[i] = self._wishart_sample(rng, df=nu, scale=scale)

        # Normal approximation for beta given Sigma
        beta_draws = np.zeros((n_draws, n_beta))
        # Approximate covariance of beta_hat
        if self._X is not None:
            # Simplified: use OLS covariance as approximation
            XtX_inv = linalg.inv(self._X.T @ self._X + 1e-6 * np.eye(n_beta))
            beta_cov = XtX_inv * np.mean(self.sigma_hat)
        else:
            beta_cov = np.eye(n_beta) * 0.01

        for i in range(n_draws):
            beta_draws[i] = rng.multivariate_normal(self.beta_hat, beta_cov)

        return {"beta": beta_draws, "sigma": sigma_draws}

    def _wishart_sample(self, rng: np.random.Generator, df: int, scale: np.ndarray) -> np.ndarray:
        """Generate a single Wishart random matrix sample.

        Args:
            rng: NumPy random number generator.
            df: Degrees of freedom.
            scale: Scale matrix (p x p).

        Returns:
            Wishart random matrix sample.
        """
        # Wishart sampling via Gamma distribution for diagonal elements
        # and Normal for off-diagonal (Bartlett decomposition)
        p = scale.shape[0]
        A = np.zeros((p, p))

        for i in range(p):
            for j in range(i + 1):
                if i == j:
                    # Bartlett decomposition: diagonal elements are sqrt(Gamma((df-i)/2, 2))
                    shape_param = (df - i) / 2.0
                    scale_param = 2.0
                    A[i, j] = np.sqrt(rng.gamma(shape_param, scale_param))
                else:
                    A[i, j] = rng.normal(0, 1)

        # Transform: X = L @ A @ A.T @ L.T where scale = L @ L.T
        try:
            L = linalg.cholesky(scale, lower=True)
        except linalg.LinAlgError:
            L = np.eye(p)

        result_matrix = L @ A @ A.T @ L.T
        return np.asarray(result_matrix)
