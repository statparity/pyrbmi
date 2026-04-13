# API Quick Reference

Common patterns for pyrbmi workflows.

## Dataset Creation

```python
from pyrbmi import RBMIDataset

# From DataFrame
ds = RBMIDataset.from_dataframe(
    df,
    subject="USUBJID",      # Required: subject identifier
    treatment="TRT01A",     # Required: treatment arm
    visit="AVISIT",         # Required: visit/timepoint
    outcome="AVAL",         # Required: outcome variable
    baseline="BASE",      # Optional: baseline covariate
    reference_arm="Placebo",  # Required: reference arm name
)
```

## Imputation Methods

```python
from pyrbmi import Imputer

# Bayesian MCMC
imputer = Imputer.bayesian(
    n_samples=200,    # Posterior samples per imputation
    n_chains=4,       # MCMC chains
    n_warmup=500,     # Warmup iterations
)

# Approximate Bayesian (faster)
imputer = Imputer.approximate_bayesian(
    n_samples=100,
)

# Conditional Mean Imputation (single draw)
imputer = Imputer.conditional_mean()
```

## Strategies

```python
from pyrbmi import Strategy

strategy = Strategy.mar()                    # Missing At Random
strategy = Strategy.jump_to_reference()      # J2R
strategy = Strategy.copy_reference()         # CR
strategy = Strategy.copy_increment()         # CIN
strategy = Strategy.last_mean_carried_forward()  # LMCF
strategy = Strategy.treatment_policy()       # Treatment policy
```

## Pooling Results

```python
from pyrbmi import pool

# Pool imputed datasets
results = pool(
    imputed_datasets,
    estimand="difference_in_means",  # or "odds_ratio", "risk_ratio"
)

# Access results
print(results.estimate)      # Point estimate
print(results.std_error)     # Standard error
print(results.conf_int())    # Confidence interval
print(results.p_value())     # P-value
print(results.summary())     # Full summary table
```

## Complete Workflow

```python
from pyrbmi import RBMIDataset, Imputer, Strategy, pool
import pandas as pd

# 1. Load data
df = pd.read_sas("adlb.xpt")  # ADaM dataset
ds = RBMIDataset.from_dataframe(
    df,
    subject="USUBJID",
    treatment="TRT01AN",
    visit="AVISITN",
    outcome="AVAL",
    baseline="BASE",
    reference_arm="Placebo",
)

# 2. Impute
imputer = Imputer.bayesian(n_samples=200, n_chains=4)
imputed = imputer.fit_impute(ds, strategy=Strategy.jump_to_reference())

# 3. Pool
results = pool(imputed, estimand="difference_in_means")
print(results.summary())
```
