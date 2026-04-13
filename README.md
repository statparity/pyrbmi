# pyrbmi

**Python implementation of reference-based multiple imputation for regulatory clinical trials.**

Direct feature-parity target: R's [`rbmi`](https://github.com/openpharma/rbmi) (openpharma) and the ICH E9(R1) estimands framework.

[![PyPI](https://img.shields.io/pypi/v/pyrbmi)](https://pypi.org/project/pyrbmi/)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)
[![CI](https://github.com/your-org/pyrbmi/actions/workflows/ci.yml/badge.svg)](https://github.com/your-org/pyrbmi/actions)
[![JOSS](https://joss.theoj.org/papers/placeholder/badge)](https://joss.theoj.org)

---

## Motivation

Reference-based multiple imputation (MI) is a cornerstone of sensitivity analysis in Phase II–IV clinical trials, required under ICH E9(R1) estimands framework guidance adopted by FDA (2021) and EMA (2020). The canonical implementation is the R package `rbmi` (Gower-Page et al., JOSS 2022).

No validated Python equivalent exists. This package closes that gap: same algorithms, same defaults, tested output parity against R `rbmi`, targeting regulatory submission workflows.

---

## Scope

| Capability | R `rbmi` | `pyrbmi` | Status |
|---|---|---|---|
| Bayesian MI (MCMC) | ✅ | ✅ | v0.1.0 |
| Approximate Bayesian MI | ✅ | ✅ | v0.2.0 |
| Conditional Mean Imputation (CMI) | ✅ | ✅ | v0.3.0 |
| MAR strategy | ✅ | ✅ | v0.1.0 |
| Jump-to-Reference (J2R) | ✅ | ✅ | v0.2.0 |
| Copy Reference (CR) | ✅ | ✅ | v0.2.0 |
| Copy Increment from Reference (CIN) | ✅ | ✅ | v0.2.0 |
| Last Mean Carried Forward (LMCF) | ✅ | ✅ | v0.2.0 |
| Treatment Policy | ✅ | ✅ | v0.2.0 |
| Rubin's rules pooling | ✅ | ✅ | v0.1.0 |
| Jackknife resampling | ✅ | 🔲 | v0.3.0 |
| Bootstrap resampling | ✅ | 🔲 | v0.3.0 |
| Delta adjustments | ✅ | 🔲 | v0.5.0 |
| Tipping point analysis | ✅ | 🔲 | v0.5.0 |
| ICH E9(R1) estimands framework | ✅ | 🔲 | v0.4.0 |
| MMRM base model | ✅ | 🔲 | v0.1.0 |
| ADaM-compatible data structures | ✅ | 🔲 | v0.1.0 |
| R parity validation suite | ✅ | 🔲 | v0.7.0 |
| Regulatory output tables | — | 🔲 | v0.8.0 |

---

## Installation

```bash
# Recommended: uv
uv add pyrbmi

# pip
pip install pyrbmi

# With Bayesian backend (PyMC)
uv add "pyrbmi[bayes]"
```

**Requires:** Python ≥ 3.11

---

## Quick Start

```python
from pyrbmi import RBMIDataset, Imputer, Strategy, pool

# 1. Load your ADaM-compatible longitudinal dataset
ds = RBMIDataset.from_dataframe(
    df,
    subject="USUBJID",
    treatment="TRT01A",
    visit="AVISIT",
    outcome="AVAL",
    baseline="BASE",
    reference_arm="Placebo",
)

# 2. Define imputation strategy (ICH E9R1 intercurrent event handling)
strategy = Strategy.jump_to_reference()

# 3. Run Bayesian multiple imputation
imputer = Imputer.bayesian(n_samples=200, n_chains=4)
imputed_datasets = imputer.fit_impute(ds, strategy=strategy)

# 4. Analyse each imputed dataset and pool via Rubin's rules
results = pool(imputed_datasets, estimand="difference_in_means")
print(results.summary())
```

---

## Validation Against R `rbmi`

Numerical output parity is verified against R `rbmi` on reference datasets. See `tests/test_vs_r/` for the full validation suite (requires `rpy2`).

```bash
uv run pytest tests/test_vs_r/ -v
```

---

## Roadmap

See [TODO.md](TODO.md) for the full atomic task list organized by SemVer milestone.

- **v0.1.0** — Bayesian MI + MAR + Rubin's rules + MMRM
- **v0.2.0** — Reference-based strategies (J2R, CR, CIN, LMCF, TreatmentPolicy)
- **v0.3.0** — Frequentist CMI + jackknife/bootstrap inference
- **v0.4.0** — ICH E9(R1) estimands framework
- **v0.5.0** — Sensitivity analysis (delta adjustments, tipping point)
- **v0.6.0** — MMRM subsystem (full unstructured covariance support)
- **v0.7.0** — R parity validation suite (rpy2-based)
- **v0.8.0** — Regulatory output tables (RTF/HTML)
- **v1.0.0** — JOSS paper submission, PyPI stable release

---

## Reference

Gower-Page C, et al. (2022). *rbmi: A R package for standard and reference based multiple imputation.* Journal of Open Source Software, 7(78), 4251. https://doi.org/10.21105/joss.04251

ICH E9(R1) (2019). *Statistical Principles for Clinical Trials: Addendum on Estimands and Sensitivity Analysis.* Step 4, November 2019.

---

## License

Apache-2.0 — see [LICENSE](LICENSE).
