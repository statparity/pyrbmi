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

        # Build design matrix and response
        x_matrix, y_vec = self._build_design_matrix(dataset)
        self._X = x_matrix
        self._y = y_vec

        # Get visit and subject counts for covariance parameterization
        self._n_visits = len(dataset._visit_order)
        self._n_subjects = dataset.df[dataset.subject_col].nunique()

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

        # Store results
        self.optimizer_result = result
        self.converged = True

        # Compute final estimates
        theta_hat = result.x
        self.sigma_hat = self._theta_to_sigma(theta_hat)
        self.beta_hat, self.log_likelihood = self._compute_final_loglik(self.sigma_hat)

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
        if self._X is None or self._y is None:
            raise RuntimeError("Model not fitted: call fit() first")

        beta_hat, logdet_sigma, sscp = self._estimate_beta(sigma)
        n_obs = len(self._y)
        n_params = self._X.shape[1]

        # Compute residual quadratic form r' V^{-1} r properly
        residuals = self._y - self._X @ beta_hat
        # For now, simplified: assume block diagonal with sigma
        # Full implementation would use proper V^{-1}
        try:
            sigma_inv = linalg.inv(sigma)
        except linalg.LinAlgError:
            sigma_inv = linalg.pinv(sigma)

        # Simplified: assume each subject has same number of visits
        # Full implementation needs proper grouping by subject
        n_subjects = self._n_subjects

        # For balanced design: V = I_n_subjects ⊗ sigma
        # V^{-1} = I_n_subjects ⊗ sigma^{-1}
        # r' V^{-1} r = sum over subjects of r_i' sigma^{-1} r_i
        # Simplified: treat all residuals together
        resid_quad = float(residuals.T @ np.kron(np.eye(n_subjects), sigma_inv) @ residuals)

        if self.reml:
            # REML: -0.5 * (n-p) * log(2π) - 0.5 * log|V| - 0.5 * log|X'V^{-1}X| - 0.5 * r'V^{-1}r
            # log|V| = n_subjects * log|sigma|
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

    def _build_design_matrix(self, dataset: RBMIDataset) -> tuple[np.ndarray, np.ndarray]:
        """Build design matrix with treatment × visit interaction.

        Creates the design matrix X using either:
        1. A custom formula (if self.formula is provided) using formulaic
        2. Default: intercept + visit dummies + baseline + treatment×visit interactions
           + additional covariates

        Args:
            dataset: The RBMIDataset instance.

        Returns:
            Tuple of (X, y) where X is the design matrix and y is the response.
        """
        df = dataset.df.copy()

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

            return np.asarray(X), np.asarray(y)

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

        return x_matrix, y_vec

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

        # Compute residual quadratic form r' V^{-1} r
        residuals = self._y - self._X @ beta_hat
        try:
            sigma_inv = linalg.inv(Sigma)
        except linalg.LinAlgError:
            sigma_inv = linalg.pinv(Sigma)

        n_subjects = self._n_subjects
        resid_quad = float(residuals.T @ np.kron(np.eye(n_subjects), sigma_inv) @ residuals)

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

        Args:
            theta: Covariance parameter vector.

        Returns:
            Tuple of (negative log-likelihood, gradient).
        """
        loglik = self._log_likelihood_value(theta)

        # Numerical gradient
        eps = 1e-6
        grad = np.zeros_like(theta)
        for i in range(len(theta)):
            theta_plus = theta.copy()
            theta_plus[i] += eps
            ll_plus = self._log_likelihood_value(theta_plus)
            grad[i] = -(ll_plus - loglik) / eps  # Negate for negative log-lik

        return -loglik, grad

    def _estimate_beta(
        self,
        sigma: np.ndarray,
    ) -> tuple[np.ndarray, float, np.ndarray]:
        """Estimate fixed effects beta given covariance matrix.

        Uses GLS: beta_hat = (X'V^{-1}X)^{-1} X'V^{-1}y

        Args:
            sigma: Covariance matrix for one subject's visits.

        Returns:
            Tuple of (beta_hat, logdet_sigma, sscp).
        """
        if self._X is None or self._y is None:
            raise RuntimeError("Model not fitted: call fit() first")

        X, y = self._X, self._y

        # For now, assume independent subjects with block diagonal structure
        # In full implementation, this would use the full V matrix
        # Simplified: use Sigma directly (assuming balanced design)

        try:
            sigma_inv = linalg.inv(sigma)
        except linalg.LinAlgError:
            # Fallback to pseudo-inverse if singular
            sigma_inv = linalg.pinv(sigma)

        # GLS estimation
        n_subjects = self._n_subjects
        xt_sinv = X.T @ np.kron(np.eye(n_subjects), sigma_inv)
        xt_sinv_x = xt_sinv @ X
        xt_sinv_y = xt_sinv @ y

        try:
            beta_hat = linalg.solve(xt_sinv_x, xt_sinv_y)
        except linalg.LinAlgError:
            beta_hat = linalg.lstsq(xt_sinv_x, xt_sinv_y)[0]

        # Compute log|S| and residual SSCP
        sign, logdet = linalg.slogdet(sigma)
        logdet_sigma = float(n_subjects * logdet) if sign > 0 else 0.0

        residuals = y - X @ beta_hat
        # Simplified SSCP (should be grouped by subject in full impl)
        sscp = residuals.reshape(-1, 1) @ residuals.reshape(1, -1)

        return beta_hat, logdet_sigma, sscp

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
