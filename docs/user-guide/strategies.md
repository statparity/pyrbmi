# Imputation Strategies

pyrbmi implements the reference-based multiple imputation strategies defined in the ICH E9(R1) estimands framework.

## Overview

| Strategy | Description | Use Case |
|----------|-------------|----------|
| MAR | Missing At Random | Standard assumption, discontinuation unrelated to outcome |
| J2R | Jump to Reference | Post-discontinuation follows reference arm trajectory |
| CR | Copy Reference | Post-discontinuation copies reference arm observations |
| CIN | Copy Increment from Reference | Post-baseline increment equals reference arm |
| LMCF | Last Mean Carried Forward | Freezes outcome at last observed value |

## MAR (Missing At Random)

The standard regulatory assumption where missing data is handled under the premise that discontinuation is unrelated to the unobserved outcome.

```python
strategy = Strategy.mar()
```

This is the primary analysis assumption in most Phase III trials.

## J2R (Jump to Reference)

After treatment discontinuation, the subject's outcome distribution "jumps" to match the reference (typically placebo) arm.

```python
strategy = Strategy.jump_to_reference()
```

**Mathematical formulation:**
- Pre-discontinuation: Subject follows their assigned treatment arm
- Post-discontinuation: Subject's mean follows reference arm, variance from reference arm

**Clinical interpretation:** Assumes treatment effect is lost after discontinuation, with disease progression similar to untreated patients.

## CR (Copy Reference)

The subject's post-baseline outcomes are replaced with draws from the reference arm's joint distribution.

```python
strategy = Strategy.copy_reference()
```

**Mathematical formulation:**
- Post-baseline: Outcome distribution identical to reference arm (including correlation structure)

**Clinical interpretation:** More extreme than J2R — assumes the subject never had any treatment effect.

## CIN (Copy Increment from Reference)

The subject's post-baseline change from baseline matches the reference arm's change from baseline.

```python
strategy = Strategy.copy_increment()
```

**Mathematical formulation:**
- Post-baseline: Increment (Y_t - Y_0) follows reference arm's increment distribution

**Clinical interpretation:** Subject maintains their baseline value but follows reference trajectory.

## LMCF (Last Mean Carried Forward)

The subject's mean outcome is frozen at their last observed value.

```python
strategy = Strategy.last_mean_carried_forward()
```

**Mathematical formulation:**
- Post-discontinuation: Mean equals last observed value, variance from within-subject residual

**Clinical interpretation:** No disease progression after discontinuation (optimistic scenario).

## Treatment Policy

Handles intercurrent events via the treatment policy estimand (ITT-like).

```python
strategy = Strategy.treatment_policy()
```

## Choosing a Strategy

The ICH E9(R1) framework recommends:

1. **Primary analysis:** MAR under treatment policy estimand
2. **Sensitivity analyses:** J2R, CR, CIN to assess robustness to departures from MAR
3. **Tipping point:** Identify thresholds where conclusions change

## Implementation Notes

All strategies are implemented via the same unified API:

```python
from pyrbmi import Strategy, Imputer

# Any strategy works with any imputation method
strategy = Strategy.jump_to_reference()
imputer = Imputer.bayesian(n_samples=200)
imputed = imputer.fit_impute(dataset, strategy=strategy)
```

The mathematical details (conditional distributions, covariance structures) are handled automatically based on the underlying MMRM model.
