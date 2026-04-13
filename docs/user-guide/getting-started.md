# Getting Started

This guide walks you through installing pyrbmi and running your first imputation analysis.

## Installation

### Prerequisites

- Python ≥ 3.11
- For Bayesian MI: A working C++ compiler (for PyMC/PyTensor)

### Install from PyPI

```bash
# Core package
pip install pyrbmi

# With Bayesian MI support
pip install "pyrbmi[bayes]"

# Development dependencies
pip install "pyrbmi[dev]"
```

### Install with uv (recommended)

```bash
# Create a new project
uv init my-analysis
cd my-analysis

# Add pyrbmi
uv add pyrbmi

# Or with Bayesian support
uv add "pyrbmi[bayes]"
```

## Your First Imputation

### 1. Prepare Your Data

Your dataset should be in "long" format with one row per subject-visit:

```python
import pandas as pd

# Example ADaM-like structure
df = pd.DataFrame({
    "USUBJID": ["S001", "S001", "S001", "S002", "S002", "S002"],
    "AVISIT": ["Week 0", "Week 4", "Week 8", "Week 0", "Week 4", "Week 8"],
    "TRT01A": ["Drug", "Drug", "Drug", "Placebo", "Placebo", "Placebo"],
    "AVAL": [10.5, 12.3, None, 11.2, 11.8, 13.1],
    "BASE": [10.5, 10.5, 10.5, 11.2, 11.2, 11.2],
})
```

### 2. Create a Dataset

```python
from pyrbmi import RBMIDataset

ds = RBMIDataset.from_dataframe(
    df,
    subject="USUBJID",
    treatment="TRT01A",
    visit="AVISIT",
    outcome="AVAL",
    baseline="BASE",
    reference_arm="Placebo",
)
```

### 3. Choose a Strategy

```python
from pyrbmi import Strategy

# MAR: Missing At Random (default regulatory assumption)
strategy_mar = Strategy.mar()

# J2R: Jump to Reference (post-discontinuation follows reference arm)
strategy_j2r = Strategy.jump_to_reference()

# CR: Copy Reference (entire post-baseline follows reference)
strategy_cr = Strategy.copy_reference()

# CIN: Copy Increment from Reference
strategy_cin = Strategy.copy_increment()

# LMCF: Last Mean Carried Forward
strategy_lmcf = Strategy.last_mean_carried_forward()
```

### 4. Run Imputation

```python
from pyrbmi import Imputer

# Bayesian MI with MCMC
imputer = Imputer.bayesian(n_samples=200, n_chains=4)
imputed_datasets = imputer.fit_impute(ds, strategy=strategy_j2r)

# Or use approximate Bayesian (faster)
imputer = Imputer.approximate_bayesian(n_samples=100)
imputed_datasets = imputer.fit_impute(ds, strategy=strategy_j2r)
```

### 5. Pool Results

```python
from pyrbmi import pool

results = pool(imputed_datasets, estimand="difference_in_means")
print(results.summary())
# Output: estimate, std.error, 95% CI, p-value
```

## Next Steps

- Learn about [imputation strategies](strategies.md)
- Explore the [API reference](../api/pyrbmi.md)
- Read about [validation against R rbmi](../validation/index.md)
