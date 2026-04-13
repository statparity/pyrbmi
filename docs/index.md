# pyrbmi

**Python implementation of reference-based multiple imputation for regulatory clinical trials.**

Direct feature-parity target: R's [`rbmi`](https://github.com/openpharma/rbmi) (openpharma) and the ICH E9(R1) estimands framework.

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

## Features

| Capability | Status |
|------------|--------|
| Bayesian MI (MCMC) | ✅ v0.1.0 |
| MAR strategy | ✅ v0.1.0 |
| Rubin's rules pooling | ✅ v0.1.0 |
| Approximate Bayesian MI | ✅ v0.2.0 |
| Jump-to-Reference (J2R) | ✅ v0.2.0 |
| Copy Reference (CR) | ✅ v0.2.0 |
| Copy Increment from Reference (CIN) | ✅ v0.2.0 |
| Last Mean Carried Forward (LMCF) | ✅ v0.2.0 |
| Conditional Mean Imputation (CMI) | ✅ v0.3.0 |

---

## Validation

Numerical output parity is verified against R `rbmi` on reference datasets.
See [Validation → R Parity Report](validation/r-parity.md) for details.

---

## References

- Gower-Page C, et al. (2022). *rbmi: A R package for standard and reference based multiple imputation.* Journal of Open Source Software, 7(78), 4251. https://doi.org/10.21105/joss.04251
- ICH E9(R1) (2019). *Statistical Principles for Clinical Trials: Addendum on Estimands and Sensitivity Analysis.* Step 4, November 2019.
