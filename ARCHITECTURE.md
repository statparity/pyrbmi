# ARCHITECTURE — pyrbmi

## 1. Design Philosophy

### Parity-First, Then Extend
Every design decision is anchored to R `rbmi` behavior. Where R `rbmi` makes a choice (default priors, covariance structure, pooling rules), `pyrbmi` matches it exactly. Extensions (e.g., additional backends, output formats) are additive and do not alter parity-path behavior.

### Validation as First-Class Concern
Output parity against R `rbmi` is not a test afterthought — it is a design constraint. The `tests/test_vs_r/` suite runs R `rbmi` via `rpy2` on the same inputs and asserts numerical agreement to configurable tolerance (default: 1e-4 relative error). This suite is the evidence artifact for institutional adoption.

### ADaM Compatibility
The core data structure maps directly to CDISC ADaM BDS (Basic Data Structure) conventions: `USUBJID`, `AVAL`, `BASE`, `AVISIT`, `TRT01A`. No proprietary formats. Input is a `pandas.DataFrame` with documented required columns.

### Dependency Minimalism
Runtime dependencies are constrained to widely validated scientific Python packages. PyMC (Bayesian backend) is optional (`pyrbmi[bayes]`). No R dependency at runtime — only in the validation dev-extra.

---

## 2. Package Structure

```
src/pyrbmi/
├── __init__.py              # Public API surface: RBMIDataset, Imputer, Strategy, pool
│
├── data/
│   ├── dataset.py           # RBMIDataset: validated wrapper around ADaM BDS DataFrames
│   ├── validators.py        # Column presence, type, visit ordering, arm definitions
│   └── covariance.py        # Covariance structure definitions (UN, CS, AR1, TOEP)
│
├── models/
│   ├── mmrm.py              # MMRM: Mixed Model for Repeated Measures
│   │                        #   - Unstructured covariance (primary)
│   │                        #   - Compound symmetry, AR(1), Toeplitz (secondary)
│   │                        #   - Posterior draws of beta, Sigma
│   └── lme.py               # Fallback LME via statsmodels (for non-MMRM paths)
│
├── impute/
│   ├── base.py              # ImputerBase ABC: fit(), impute(), fit_impute()
│   ├── bayesian.py          # BayesianImputer: MCMC posterior draws via PyMC v5
│   │                        #   - Wishart prior on Sigma (matches rbmi default)
│   │                        #   - Normal prior on beta coefficients
│   │                        #   - n_samples, n_tune, n_chains configurable
│   ├── approx_bayes.py      # ApproxBayesianImputer: analytical approximation
│   │                        #   - Matches rbmi method="approxbayes"
│   └── cmi.py               # CMImputer: Conditional mean imputation
│                            #   - Frequentist, no MCMC
│                            #   - Supports jackknife and bootstrap variance
│
├── strategies/
│   ├── base.py              # InterurrentEventStrategy ABC
│   │                        #   - apply(dataset, draws) → imputed values
│   ├── mar.py               # MissingAtRandom: baseline MAR assumption
│   ├── j2r.py               # JumpToReference: subject switches to reference trajectory
│   ├── cr.py                # CopyReference: copy residuals from reference arm
│   ├── cin.py               # CopyIncrementFromReference: delta from reference post-ICE
│   ├── lmcf.py              # LastMeanCarriedForward: carry forward mean trajectory
│   ├── policy.py            # TreatmentPolicy: regardless of ICE occurrence
│   ├── stratum.py           # PrincipalStratum: conditional on ICE stratum
│   └── hypothetical.py      # HypotheticalStrategy: counterfactual under intervention
│
├── estimands/
│   ├── framework.py         # Estimand: ICH E9(R1) 4-attribute definition
│   │                        #   Attributes: population, variable, ICE-strategy,
│   │                        #   population-level summary
│   ├── intercurrent.py      # InterurrentEvent: event type, timing, assignment
│   └── population.py        # TargetPopulation: inclusion/exclusion predicate
│
├── inference/
│   ├── rubin.py             # RubinsRules: pool point estimates + variance
│   │                        #   - Supports df correction (Barnard-Rubin)
│   │                        #   - Returns: estimate, se, df, t, p, CI
│   ├── contrast.py          # TreatmentContrast: difference, ratio, LS means
│   └── bootstrap.py         # BootstrapPooler: non-parametric variance estimation
│
├── sensitivity/
│   ├── tipping.py           # TippingPoint: sweep delta to find null-crossing
│   └── delta.py             # DeltaAdjustment: additive/multiplicative offset post-ICE
│
└── report/
    ├── tables.py            # AnalysisTable: regulatory-grade summary tables
    └── rtf.py               # RTF output (optional, for submission packages)
```

---

## 3. Core Data Flow

```
DataFrame (ADaM BDS)
        │
        ▼
  RBMIDataset.from_dataframe()
  [validates columns, encodes arms, orders visits]
        │
        ▼
  Imputer.fit(dataset)
  [fits MMRM on observed data → posterior of (β, Σ)]
        │
        ▼
  Strategy.apply(dataset, draws)
  [uses posterior draws to impute under ICE assumption]
        │
        ▼
  List[ImputedDataset]  (M imputed complete datasets)
        │
        ▼
  AnalysisModel.fit(imputed_dataset) × M
  [fits analysis model on each complete dataset]
        │
        ▼
  pool(results)
  [Rubin's rules → point estimate, variance, df, p-value, CI]
        │
        ▼
  PooledResult
  [summary(), to_dataframe(), to_table()]
```

---

## 4. MMRM Subsystem

The MMRM (Mixed Model for Repeated Measures) is the base model for longitudinal clinical trial data. It is the single most technically complex component.

**Model specification:**
```
Y_ij = Xβ + ε_ij
ε_i ~ N(0, Σ)
```
Where:
- `Y_ij` = outcome for subject `i` at visit `j`
- `X` = design matrix: treatment × visit interaction + baseline + covariates
- `Σ` = visit-by-visit covariance matrix (unstructured by default)

**Implementation strategy:**
- Primary: `statsmodels.MixedLM` with manual covariance parameterization
- Secondary: custom log-likelihood via `scipy.optimize.minimize` (L-BFGS-B)
- Fallback: `pymmrm` wrapper if available
- Validation: compare REML estimates against R `mmrm` package on reference datasets

**Posterior draws for imputation:**
- Frequentist path (CMI): point estimate of (β, Σ) only
- Bayesian path: posterior samples via PyMC — Wishart(ν, Ψ) prior on Σ⁻¹, Normal prior on β

---

## 5. ICH E9(R1) Estimands Framework

An `Estimand` object formalizes the four ICH E9(R1) attributes:

```python
estimand = Estimand(
    population=TargetPopulation(criteria="AGE >= 18 and ITTFL == 'Y'"),
    variable="change from baseline at Week 24",
    intercurrent_event=InterurrentEvent(
        event="treatment discontinuation",
        strategy=JumpToReference(),
    ),
    population_summary="difference in means (active - placebo)",
)
```

This object is passed to the `Imputer` and `pool()` pipeline, driving which strategy is applied and how the population-level summary is computed.

---

## 6. Validation Framework

The `tests/test_vs_r/` suite requires `rpy2` (dev extra only):

```
tests/test_vs_r/
├── conftest.py           # rpy2 setup, R rbmi install check
├── fixtures/             # Pre-computed R rbmi outputs (JSON/CSV) for CI without R
├── test_mar_parity.py    # MAR imputation: compare pooled estimates
├── test_j2r_parity.py    # J2R: compare per-visit treatment differences
├── test_rubin_parity.py  # Rubin's rules: compare SE, df, CI
├── test_cmi_parity.py    # CMI + jackknife variance: compare SEs
└── test_tipping_parity.py
```

For CI environments without R, fixtures contain pre-serialized R outputs that are used as reference instead of live `rpy2` calls.

---

## 7. Dependency Stack

### Runtime
| Package | Version | Role |
|---|---|---|
| `numpy` | ≥2.0 | Numerical arrays |
| `scipy` | ≥1.14 | Optimization, distributions, stats |
| `pandas` | ≥2.2 | ADaM DataFrame handling |
| `statsmodels` | ≥0.14 | MixedLM, GLM base |
| `formulaic` | ≥1.0 | R-formula syntax for model specification |
| `patsy` | ≥0.5 | Fallback formula parser |

### Optional: Bayesian backend
| Package | Version | Role |
|---|---|---|
| `pymc` | ≥5.16 | MCMC posterior sampling |
| `pytensor` | ≥2.20 | PyMC computation graph |
| `arviz` | ≥0.20 | MCMC diagnostics |
| `nutpie` | ≥0.13 | Fast NUTS sampler (optional speedup) |

### Dev / Validation
| Package | Version | Role |
|---|---|---|
| `rpy2` | ≥3.5 | R `rbmi` output comparison |
| `pytest` | ≥8.0 | Test runner |
| `pytest-cov` | ≥5.0 | Coverage |
| `hypothesis` | ≥6.0 | Property-based testing |
| `ruff` | ≥0.6 | Linting + formatting |
| `mypy` | ≥1.11 | Type checking |

---

## 8. Design Constraints and Non-Goals

**Constraints:**
- Output must be numerically equivalent to R `rbmi` on reference datasets (tolerance 1e-4)
- No R dependency at runtime
- ADaM BDS column conventions are the standard data interface — no custom formats
- Public API surface is stable at v1.0.0 (semver strictly followed)

**Non-goals (v1.0.0 scope):**
- Full `admiral` ADaM derivation pipeline (separate package, separate effort)
- Non-continuous endpoints (binary, time-to-event) — planned post-v1.0.0
- Direct FDA eCTD submission integration — tooling only, not a submission system
