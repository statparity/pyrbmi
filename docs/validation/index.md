# Validation

pyrbmi maintains strict numerical parity with R's `rbmi` package, the reference implementation for regulatory submissions.

## Validation Strategy

Our validation approach follows FDA/EMA guidance on software validation for clinical trials:

1. **Unit Tests:** All functions have unit tests with ≥90% coverage
2. **R Parity Tests:** Numerical output compared against R `rbmi` on identical datasets
3. **Reference Datasets:** Tests use publicly available or synthetic datasets with known properties
4. **Tolerance Criteria:** Statistical results match within machine precision (1e-10 relative)

## R Parity Testing

The R parity test suite runs weekly against the latest R `rbmi` release:

```bash
# Run R parity tests locally (requires R + rpy2)
uv run pytest tests/test_vs_r/ -v
```

### Test Coverage

| Component | R Test Coverage |
|-----------|-----------------|
| MAR imputation | ✅ |
| J2R imputation | ✅ |
| CR imputation | ✅ |
| CIN imputation | ✅ |
| LMCF imputation | ✅ |
| Rubin's rules pooling | ✅ |
| MMRM covariance structures | ✅ |

### Automated Validation

The validation workflow runs:

- **Weekly:** Against latest R `rbmi` from CRAN
- **On PR:** When R-related code changes
- **Results:** Published as workflow artifacts

See [R Parity Report](r-parity.md) for the latest validation results.

## Validation Report

The full validation report (v0.7.0 milestone) will include:

- Numerical comparison tables
- Tolerance analysis
- Edge case documentation
- Regulatory submission notes

---

*Last updated: [Placeholder for automated report]*
