# Major Dependency Upgrade Checklist

> Template for tracking major version dependency upgrades that require R parity validation.

## Current State (Pinned for R Parity)

| Package | Current | Latest Major | Risk Level |
|---------|---------|--------------|------------|
| numpy | >=1.24 | 2.x | **HIGH** - Core numerical operations |
| pandas | >=2.0 | 3.x | **HIGH** - Data structures |
| scipy | >=1.10 | 2.x | **MEDIUM** - Statistical functions |
| pymc | >=5.10 | 6.x | **HIGH** - Bayesian inference |
| pytensor | >=2.18 | 3.x | **HIGH** - Tensor operations (pymc dep) |

## Upgrade Checklist

### Phase 1: Preparation
- [ ] Review upstream changelog for breaking changes
- [ ] Create `upgrade/<package>-<version>` branch
- [ ] Update `pyproject.toml` version constraint
- [ ] Run `uv lock --upgrade-package <package>`

### Phase 2: Compatibility
- [ ] Run `uv run ruff check .` - fix any deprecated API warnings
- [ ] Run `uv run mypy src/pyrbmi` - check type compatibility
- [ ] Run `uv run pytest tests/unit/` - unit tests pass
- [ ] Fix any deprecation warnings in test output

### Phase 3: R Parity Validation (CRITICAL)
- [ ] Run `uv run pytest tests/test_vs_r/` - R parity tests pass
- [ ] Check numerical tolerance - must match R `rbmi` within 1e-6
- [ ] If failures: investigate numerical differences
- [ ] Document any expected differences in `docs/validation/r-parity.md`

### Phase 4: Integration
- [ ] Run full CI suite: `act push` or wait for GitHub Actions
- [ ] Check documentation builds: `uv run mkdocs build`
- [ ] Update `CHANGELOG.md` with upgrade notes
- [ ] Update `NOTICE` if license changed

### Phase 5: Merge
- [ ] Create PR with `[MAJOR]` prefix in title
- [ ] Request review from `@statparity/maintainers`
- [ ] Merge only after R parity validation confirmed

## Blocked Upgrades

The following major versions are **blocked** via `.github/dependabot.yml` `ignore` rules:

```yaml
# These require manual R parity validation
- dependency-name: "numpy"
  update-types: ["version-update:semver-major"]
- dependency-name: "pandas"
  update-types: ["version-update:semver-major"]
- dependency-name: "scipy"
  update-types: ["version-update:semver-major"]
```

To unblock: Remove from `dependabot.yml` after successful manual upgrade.

## Risk Assessment

### numpy 2.x
- **Breaking**: Array scalar representation, type promotion changes
- **R Parity Risk**: HIGH - May affect imputation draws
- **Mitigation**: Pin to <2 until validated

### pandas 3.x
- **Breaking**: NA handling, Index behavior changes
- **R Parity Risk**: HIGH - Data structure core to analysis
- **Mitigation**: Pin to <3 until validated

### scipy 2.x
- **Breaking**: Stats API changes
- **R Parity Risk**: MEDIUM - Used for distributions
- **Mitigation**: Test all statistical functions

### pymc 6.x / pytensor 3.x
- **Breaking**: Model API changes, sampler defaults
- **R Parity Risk**: HIGH - Bayesian inference engine
- **Mitigation**: Validate MCMC convergence vs R
