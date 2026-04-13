# TODO — pyrbmi

Atomic task list. Format: `[ ]` open, `[x]` done, `[~]` in progress.
Each task is a PR-sized unit of work. Milestones map to SemVer releases.

---

## Phase 0 — Project Setup

### 0.1 Repository & Tooling
- [x] 0.1.1 Initialize repo with `uv init --lib pyrbmi`
- [x] 0.1.2 Configure `pyproject.toml`: name, version `0.0.1.dev0`, description, authors, Python ≥3.11
- [x] 0.1.3 Add `[project.optional-dependencies]`: `bayes = [pymc, pytensor, arviz]`, `dev = [rpy2, pytest, ...]`
- [x] 0.1.4 Configure `ruff` (linting + formatting): `line-length=100`, `target-version="py311"`
- [x] 0.1.5 Configure `mypy`: strict mode, `src` layout
- [x] 0.1.6 Add `.gitignore`, `.python-version` (3.11)
- [x] 0.1.7 Add `uv.lock` to version control

### 0.2 CI/CD Pipeline

#### 0.2.A Hot Path — Python-only (every commit, no R)
- [ ] 0.2.1 GitHub Actions: `ci.yml` — lint (ruff), typecheck (mypy), test (pytest) on push/PR
  - [ ] 0.2.1.a No R dependency — pure Python environment only
  - [ ] 0.2.1.b `uv sync --extra bayes` to include PyMC optional deps
- [ ] 0.2.2 CI matrix: Python 3.11, 3.12, 3.13 × Ubuntu, macOS
- [ ] 0.2.3 GitHub Actions: `release.yml` — build + publish to PyPI on tag `v*`
- [ ] 0.2.4 Configure Codecov or equivalent (coverage ≥ 90% gate)
- [ ] 0.2.5 Add Dependabot config for Python dependencies
- [ ] 0.2.6 Add `CODEOWNERS`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`

#### 0.2.B R Validation Base Image — build once, reuse forever
> Solves: R package compilation from source taking 2-5 min per package on Linux.
> Strategy: pre-built Docker image using r2u (Rocker project) — serves R packages
> as pre-compiled .deb via apt. Install time: 5-10 sec vs 2-5 min from source.

- [ ] 0.2.7 Create `docker/r-validation/Dockerfile`
  - [ ] 0.2.7.a Base: `ubuntu:24.04`
  - [ ] 0.2.7.b Install r2u (CRAN-as-apt, Rocker project) — pre-built .deb binaries
  - [ ] 0.2.7.c `install2.r rbmi rstan` — seconds not minutes via apt
  - [ ] 0.2.7.d Install Python + uv + rpy2 in same image
  - [ ] 0.2.7.e Pin image with `LABEL org.opencontainers.image.version`
- [ ] 0.2.8 GitHub Actions: `build-r-base.yml` — build and push to `ghcr.io/your-org/pyrbmi-r-base`
  - [ ] 0.2.8.a Trigger: weekly schedule + on change to `docker/r-validation/Dockerfile`
  - [ ] 0.2.8.b Tag: `ghcr.io/your-org/pyrbmi-r-base:r{R_VERSION}-rbmi{RBMI_VERSION}`
  - [ ] 0.2.8.c Cache layers: apt lists, r2u package index, R library dir
- [ ] 0.2.9 Add `renv.lock` (R side) — pins rbmi and rstan versions used in validation
  - [ ] 0.2.9.a Trigger `build-r-base.yml` rebuild on `renv.lock` change

#### 0.2.C R Parity Workflow — scheduled, uses pre-built image
- [ ] 0.2.10 GitHub Actions: `validate-r.yml`
  - [ ] 0.2.10.a `container: ghcr.io/your-org/pyrbmi-r-base:latest` — no R compilation at runtime
  - [ ] 0.2.10.b Trigger: weekly schedule + manual dispatch
  - [ ] 0.2.10.c Steps: `uv sync` → `pytest tests/test_vs_r/ -v`
  - [ ] 0.2.10.d Upload parity report as workflow artifact
  - [ ] 0.2.10.e Fail PR if parity report regresses (tolerance breach)

#### 0.2.D Local Dev R Setup
- [ ] 0.2.11 Add `.Rprofile` to repo root (dev convenience, gitignored from src/)
  - [ ] 0.2.11.a Set Posit Package Manager binary mirror: `options(repos = c(CRAN = "https://packagemanager.posit.co/cran/__linux__/noble/latest"))`
  - [ ] 0.2.11.b Eliminates source compilation locally — same 5-10 sec install as r2u
- [ ] 0.2.12 Document R local setup in `CONTRIBUTING.md`: install via binary mirror, not CRAN default

### 0.3 Documentation Infrastructure
- [ ] 0.3.1 Initialize MkDocs + mkdocstrings (Google-style docstrings)
- [ ] 0.3.2 Configure `docs/` structure: API reference, User Guide, Validation Report
- [ ] 0.3.3 Add `docs/validation/` — placeholder for R parity report (populated at v0.7.0)
- [ ] 0.3.4 Add GitHub Pages deployment action

### 0.4 License & Legal
- [ ] 0.4.1 Add `LICENSE` file (Apache-2.0, full text)
- [ ] 0.4.2 Add SPDX header template for source files: `# SPDX-License-Identifier: Apache-2.0`
- [ ] 0.4.3 Add `NOTICE` file (attribution for upstream references: R `rbmi`, ICH E9(R1))

---

## Milestone v0.1.0 — Bayesian MI + MAR + Rubin's Rules + MMRM

> Goal: end-to-end working pipeline for the simplest case (MAR, continuous outcome, Bayesian MI).

### 1.1 Data Layer (`pyrbmi.data`)
- [ ] 1.1.1 Implement `RBMIDataset` dataclass
  - [ ] 1.1.1.a Fields: `df`, `subject_col`, `treatment_col`, `visit_col`, `outcome_col`, `baseline_col`, `reference_arm`
  - [ ] 1.1.1.b `from_dataframe()` classmethod: validates all required columns present
  - [ ] 1.1.1.c Validate visit ordering (categorical ordered or sortable)
  - [ ] 1.1.1.d Validate no duplicate (subject, visit) combinations
  - [ ] 1.1.1.e Encode treatment arms as integer indices internally
- [ ] 1.1.2 Implement `validators.py`
  - [ ] 1.1.2.a `validate_columns(df, required)` — raises `RBMIDataError` with clear message
  - [ ] 1.1.2.b `validate_no_missing_baseline()` — baseline must be complete
  - [ ] 1.1.2.c `validate_arm_labels(df, reference_arm)` — reference arm must exist in data
- [ ] 1.1.3 Implement `CovarianceStructure` enum: `UNSTRUCTURED`, `COMPOUND_SYMMETRY`, `AR1`, `TOEPLITZ`
- [ ] 1.1.4 Write unit tests for all validators (happy path + error cases)
  - [ ] 1.1.4.a Test missing column detection
  - [ ] 1.1.4.b Test duplicate visit detection
  - [ ] 1.1.4.c Test invalid reference arm

### 1.2 MMRM Base Model (`pyrbmi.models.mmrm`)
- [ ] 1.2.1 Implement `MMRM` class
  - [ ] 1.2.1.a `__init__(covariance=UNSTRUCTURED, reml=True)`
  - [ ] 1.2.1.b `fit(dataset)` — builds design matrix, fits REML
  - [ ] 1.2.1.c Store: `beta_hat`, `sigma_hat`, `log_likelihood`, convergence status
  - [ ] 1.2.1.d Raise `MMRMConvergenceError` if optimizer fails to converge
- [ ] 1.2.2 Design matrix construction
  - [ ] 1.2.2.a Treatment × visit interaction terms
  - [ ] 1.2.2.b Baseline covariate (continuous)
  - [ ] 1.2.2.c Configurable additional covariates
  - [ ] 1.2.2.d Use `formulaic` for formula parsing
- [ ] 1.2.3 Unstructured covariance parameterization
  - [ ] 1.2.3.a Cholesky parameterization for positive-definiteness
  - [ ] 1.2.3.b REML log-likelihood implementation
  - [ ] 1.2.3.c `scipy.optimize.minimize` with L-BFGS-B
- [ ] 1.2.4 Posterior draw method (for Bayesian path)
  - [ ] 1.2.4.a `draw_posterior_params(n_draws)` — Wishart + Normal conjugate draws
- [ ] 1.2.5 MMRM unit tests
  - [ ] 1.2.5.a Fit on simulated complete data, check beta recovery
  - [ ] 1.2.5.b Verify REML < ML log-likelihood (expected)
  - [ ] 1.2.5.c Convergence on standard trial datasets (`antidepressant` from rbmi)

### 1.3 Bayesian Imputer (`pyrbmi.impute.bayesian`)
- [ ] 1.3.1 Implement `BayesianImputer(n_samples, n_tune, n_chains, random_seed)`
- [ ] 1.3.2 PyMC model construction
  - [ ] 1.3.2.a Wishart prior on precision matrix (matches rbmi default ν = n_visits + 1)
  - [ ] 1.3.2.b Normal prior on β ~ N(β_hat, (X'X)⁻¹ ⊗ Σ)
  - [ ] 1.3.2.c NUTS sampler via PyMC
- [ ] 1.3.3 `fit(dataset)` — run MCMC, store `InferenceData`
- [ ] 1.3.4 `impute(dataset, strategy, n_imputations)` → `List[ImputedDataset]`
  - [ ] 1.3.4.a Sample n_imputations draws from posterior
  - [ ] 1.3.4.b Apply strategy to generate imputed outcomes for missing visits
  - [ ] 1.3.4.c Return M complete datasets
- [ ] 1.3.5 MCMC diagnostics
  - [ ] 1.3.5.a R-hat check (warn if R-hat > 1.01)
  - [ ] 1.3.5.b ESS check (warn if bulk ESS < 100 per chain)
  - [ ] 1.3.5.c Expose `diagnostics` property (ArviZ summary)
- [ ] 1.3.6 Bayesian imputer tests
  - [ ] 1.3.6.a Check imputed dataset count matches `n_imputations`
  - [ ] 1.3.6.b Check no missing values in imputed datasets
  - [ ] 1.3.6.c Check imputed values are within plausible range

### 1.4 MAR Strategy (`pyrbmi.strategies.mar`)
- [ ] 1.4.1 Implement `MissingAtRandom` strategy
  - [ ] 1.4.1.a `apply(dataset, posterior_draw)` — impute from arm-specific posterior
  - [ ] 1.4.1.b No post-ICE adjustment (pure MAR)
- [ ] 1.4.2 Write strategy unit tests

### 1.5 Rubin's Rules (`pyrbmi.inference.rubin`)
- [ ] 1.5.1 Implement `pool(results, estimand_type)` function
  - [ ] 1.5.1.a Input: `List[AnalysisResult]` each with `estimate`, `variance`
  - [ ] 1.5.1.b Within-imputation variance: mean of M variances
  - [ ] 1.5.1.c Between-imputation variance: variance of M estimates
  - [ ] 1.5.1.d Total variance: within + (1 + 1/M) × between
  - [ ] 1.5.1.e Degrees of freedom: Barnard-Rubin correction
  - [ ] 1.5.1.f Return `PooledResult`: estimate, se, df, t_stat, p_value, ci_lower, ci_upper
- [ ] 1.5.2 `PooledResult.summary()` — formatted string output
- [ ] 1.5.3 `PooledResult.to_dataframe()` — pandas DataFrame output
- [ ] 1.5.4 Rubin's rules unit tests
  - [ ] 1.5.4.a Known input → verify formula math exactly
  - [ ] 1.5.4.b Verify large M → converges toward single-imputation estimate

### 1.6 Public API (`pyrbmi/__init__.py`)
- [ ] 1.6.1 Export: `RBMIDataset`, `Imputer`, `Strategy`, `pool`, `PooledResult`
- [ ] 1.6.2 `Imputer.bayesian(...)` factory classmethod
- [ ] 1.6.3 `Strategy.mar()` factory classmethod
- [ ] 1.6.4 Add `__version__ = "0.1.0"`

### 1.7 v0.1.0 Integration Test
- [ ] 1.7.1 End-to-end test: simulate antidepressant-style dataset, run full pipeline, check output structure
- [ ] 1.7.2 Verify `pool()` output is a valid `PooledResult` with all fields populated
- [ ] 1.7.3 Tag `v0.1.0`, publish to TestPyPI, verify install

---

## Milestone v0.2.0 — Reference-Based Strategies

> Goal: implement all ICH E9(R1) reference-based intercurrent event strategies.

### 2.1 Strategies
- [ ] 2.1.1 `JumpToReference` (`pyrbmi.strategies.j2r`)
  - [ ] 2.1.1.a Post-ICE: subject's trajectory jumps to reference arm trajectory
  - [ ] 2.1.1.b Handle ICE timing (partial visit completion)
  - [ ] 2.1.1.c Unit tests: verify post-ICE values use reference arm posterior
- [ ] 2.1.2 `CopyReference` (`pyrbmi.strategies.cr`)
  - [ ] 2.1.2.a Post-ICE: copy residuals from reference arm subjects
  - [ ] 2.1.2.b Unit tests
- [ ] 2.1.3 `CopyIncrementFromReference` (`pyrbmi.strategies.cin`)
  - [ ] 2.1.3.a Post-ICE: add reference arm increment to last observed value
  - [ ] 2.1.3.b Unit tests
- [ ] 2.1.4 `LastMeanCarriedForward` (`pyrbmi.strategies.lmcf`)
  - [ ] 2.1.4.a Post-ICE: carry forward mean trajectory (not last observation)
  - [ ] 2.1.4.b Unit tests
- [ ] 2.1.5 `TreatmentPolicy` (`pyrbmi.strategies.policy`)
  - [ ] 2.1.5.a Impute regardless of ICE occurrence
  - [ ] 2.1.5.b Unit tests

### 2.2 Strategy factory methods
- [ ] 2.2.1 Add `Strategy.jump_to_reference()`, `Strategy.copy_reference()`, etc.
- [ ] 2.2.2 Strategy serialization: `to_dict()` / `from_dict()` for reproducibility

### 2.3 `ApproxBayesianImputer` (`pyrbmi.impute.approx_bayes`)
- [ ] 2.3.1 Analytical approximation to posterior (matches `rbmi method="approxbayes"`)
- [ ] 1.3.2 No MCMC required — faster for large datasets
- [ ] 2.3.3 Unit tests: compare to BayesianImputer on small datasets (should be similar)

### 2.4 v0.2.0 Integration Tests
- [ ] 2.4.1 Run J2R strategy end-to-end on reference dataset
- [ ] 2.4.2 Verify that J2R pooled estimate is more conservative than MAR (expected direction)
- [ ] 2.4.3 Tag `v0.2.0`, publish to PyPI

---

## Milestone v0.3.0 — Frequentist CMI + Resampling Inference

### 3.1 Conditional Mean Imputer (`pyrbmi.impute.cmi`)
- [ ] 3.1.1 `CMImputer`: conditional mean imputation (no randomness, uses β_hat)
- [ ] 3.1.2 `fit(dataset)` — REML MMRM fit only
- [ ] 3.1.3 `impute(dataset, strategy)` — deterministic imputation

### 3.2 Jackknife Variance (`pyrbmi.inference.rubin` + `bootstrap`)
- [ ] 3.2.1 Leave-one-out jackknife resampling over subjects
- [ ] 3.2.2 `JackknifePooler`: variance from jackknife replications
- [ ] 3.2.3 `BootstrapPooler`: variance from bootstrap replications (parametric option)
- [ ] 3.2.4 Unit tests: verify jackknife SE is reasonable

### 3.3 v0.3.0 Integration Tests
- [ ] 3.3.1 CMI + jackknife end-to-end on reference dataset
- [ ] 3.3.2 Tag `v0.3.0`, publish to PyPI

---

## Milestone v0.4.0 — ICH E9(R1) Estimands Framework

### 4.1 Estimand Objects (`pyrbmi.estimands`)
- [ ] 4.1.1 `Estimand` dataclass with 4 ICH E9(R1) attributes
- [ ] 4.1.2 `TargetPopulation`: predicate on DataFrame (filter expression)
- [ ] 4.1.3 `InterurrentEvent`: event name, timing column, strategy assignment
- [ ] 4.1.4 `PopulationSummary` enum: `DIFFERENCE_IN_MEANS`, `LS_MEANS_DIFFERENCE`, `RATIO`
- [ ] 4.1.5 `Estimand.validate()` — checks consistency of attributes
- [ ] 4.1.6 `Estimand` serialization: `to_yaml()` / `from_yaml()` for SAP documentation

### 4.2 Pipeline Integration
- [ ] 4.2.1 `Imputer.fit_impute(dataset, estimand)` — uses estimand to select strategy
- [ ] 4.2.2 `pool(results, estimand)` — uses estimand to select summary measure
- [ ] 4.2.3 `PooledResult` includes estimand metadata in output

### 4.3 Multiple Estimands (sensitivity workflow)
- [ ] 4.3.1 `run_estimands(dataset, estimands: List[Estimand])` — run multiple in parallel
- [ ] 4.3.2 Return `Dict[str, PooledResult]` keyed by estimand name

### 4.4 Tests
- [ ] 4.4.1 Define two estimands (MAR primary, J2R sensitivity), verify both run
- [ ] 4.4.2 Verify YAML round-trip preserves estimand definition
- [ ] 4.4.3 Tag `v0.4.0`, publish to PyPI

---

## Milestone v0.5.0 — Sensitivity Analysis

### 5.1 Delta Adjustments (`pyrbmi.sensitivity.delta`)
- [ ] 5.1.1 `DeltaAdjustment`: additive offset applied to post-ICE imputed values
- [ ] 5.1.2 `MultiplicativeDelta`: multiplicative version
- [ ] 5.1.3 Apply delta in `Strategy.apply()` as optional post-processing
- [ ] 5.1.4 Unit tests

### 5.2 Tipping Point Analysis (`pyrbmi.sensitivity.tipping`)
- [ ] 5.2.1 `TippingPointAnalysis`: sweep delta range, find delta at which p > alpha
- [ ] 5.2.2 Output: delta value at null-crossing, plot-ready DataFrame
- [ ] 5.2.3 `TippingPointResult.plot()` — matplotlib figure
- [ ] 5.2.4 Unit tests: verify monotonic relationship between delta and p-value

### 5.3 v0.5.0 Tests + Tag

---

## Milestone v0.6.0 — MMRM Full Covariance Support

### 6.1 Covariance Structures
- [ ] 6.1.1 `CompoundSymmetry`: 2-parameter (sigma², rho)
- [ ] 6.1.2 `AR1`: autoregressive lag-1
- [ ] 6.1.3 `Toeplitz`: banded structure
- [ ] 6.1.4 `HeterogeneousCS`, `HeterogeneousAR1`: heterogeneous variances

### 6.2 Model Selection
- [ ] 6.2.1 `MMRM.aic()`, `MMRM.bic()` for covariance structure comparison
- [ ] 6.2.2 `select_covariance(dataset, structures)` — fit all, return best by AIC

### 6.3 Performance
- [ ] 6.3.1 Profile MMRM fit on large datasets (N=500, J=6 visits)
- [ ] 6.3.2 Add optional `numba` JIT for likelihood evaluation if needed
- [ ] 6.3.3 Tag `v0.6.0`

---

## Milestone v0.7.0 — R Parity Validation Suite

> This milestone is the primary institutional evidence artifact.

### 7.1 Validation Infrastructure
- [ ] 7.1.1 Create `tests/test_vs_r/` with `rpy2`-based test runner
- [ ] 7.1.2 Install R `rbmi` in CI validation environment
- [ ] 7.1.3 Serialize R reference outputs to `tests/test_vs_r/fixtures/` (JSON)

### 7.2 Parity Tests
- [ ] 7.2.1 MAR + Bayesian MI: compare pooled estimate, SE, p-value (tol=1e-4)
- [ ] 7.2.2 J2R + Bayesian MI: compare pooled estimate
- [ ] 7.2.3 CR + Bayesian MI: compare pooled estimate
- [ ] 7.2.4 CIN + Bayesian MI: compare pooled estimate
- [ ] 7.2.5 LMCF: compare pooled estimate
- [ ] 7.2.6 CMI + jackknife: compare SE
- [ ] 7.2.7 Tipping point: compare delta at null-crossing
- [ ] 7.2.8 Rubin's rules: compare df (Barnard-Rubin)
- [ ] 7.2.9 MMRM: compare β_hat, Σ_hat (unstructured, REML)

### 7.3 Validation Report
- [ ] 7.3.1 Auto-generate `docs/validation/parity_report.md` from test results
- [ ] 7.3.2 Include: dataset description, R version, rbmi version, pyrbmi version, test outcomes, numerical diffs
- [ ] 7.3.3 Publish validation report to docs site
- [ ] 7.3.4 Tag `v0.7.0`

---

## Milestone v0.8.0 — Regulatory Output Tables

### 8.1 Analysis Tables (`pyrbmi.report.tables`)
- [ ] 8.1.1 `AnalysisTable`: treatment difference table (estimate, CI, p)
- [ ] 8.1.2 Column format: matches regulatory SAP table shells
- [ ] 8.1.3 `to_dataframe()`, `to_html()`, `to_rtf()` (optional)
- [ ] 8.1.4 `PooledResult.summary_table()` convenience method

### 8.2 Tag `v0.8.0`

---

## Milestone v1.0.0 — Stable Release + JOSS Paper

### 9.1 Pre-release
- [ ] 9.1.1 Full API review: deprecate any experimental interfaces
- [ ] 9.1.2 Docs: complete User Guide with worked examples (antidepressant dataset)
- [ ] 9.1.3 Docs: Validation Report finalized and linked from README
- [ ] 9.1.4 Coverage ≥ 90% verified

### 9.2 JOSS Submission
- [ ] 9.2.1 Write `paper.md` (JOSS format): summary, statement of need, R parity, API example
- [ ] 9.2.2 Write `paper.bib`: cite rbmi (Gower-Page 2022), ICH E9(R1), PyMC, statsmodels
- [ ] 9.2.3 Submit to JOSS (https://joss.theoj.org)
- [ ] 9.2.4 Address reviewer comments

### 9.3 PyPI Stable
- [ ] 9.3.1 Tag `v1.0.0`
- [ ] 9.3.2 Publish to PyPI (production)
- [ ] 9.3.3 Announce: R-bloggers, PyPI, Pharmaverse community, pharmastat mailing lists

---

## Backlog (Post v1.0.0)

- [ ] Binary endpoints (logistic MMRM analog)
- [ ] Time-to-event endpoints (competing risks under ICE strategies)
- [ ] Non-normal outcomes (count data, ordinal)
- [ ] Multiple ICEs per subject
- [ ] Integration with `admiral-py` (when available) for ADaM pipeline
- [ ] GPU acceleration via JAX backend (optional)
