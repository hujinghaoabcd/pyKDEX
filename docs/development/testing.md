# Testing

```bash
python -m pip install -e ".[test]"
python -m pytest -q
python examples/run_all.py
python examples/validate_coverage.py
```

Tests cover analytical values, numerical mass conservation, weighted density
and intensity semantics, failed-refit cleanup, input ownership, DataFrame
schema checks, chunk invariance, geospatial export, examples, and packaging.
