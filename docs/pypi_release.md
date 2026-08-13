# PyPI Release Notes

The PyPI distribution name is `tradearena-benchmark`.

The shorter name `tradearena` is already occupied on PyPI by an unrelated
project, so this repository keeps the user-facing import namespace and CLI as
`tradearena` while publishing the installable distribution as
`tradearena-benchmark`.

## Local Build Check

```bash
python -m pip install --upgrade build twine
python -m build
python -m twine check dist/*
```

Expected artifacts:

```text
dist/tradearena_benchmark-<version>-py3-none-any.whl
dist/tradearena_benchmark-<version>.tar.gz
```

## Trusted Publishing

Recommended production path:

1. In PyPI, create or reserve the project `tradearena-benchmark`.
2. Add a pending trusted publisher:
   - Owner: `weich97`
   - Repository: `TradeArena`
   - Workflow: `release.yml`
   - Environment: `pypi`
3. In the GitHub repository, set repository variable `PYPI_PUBLISH=true`.
4. Push a release tag such as `v0.2.0`.

The release workflow builds the wheel and source distribution, checks metadata,
uploads release assets, and only publishes to PyPI when `PYPI_PUBLISH=true`.

## Token Upload Fallback

If Trusted Publishing is not configured yet, create a PyPI API token scoped to
the `tradearena-benchmark` project after reserving it, then upload from a clean
checkout:

```powershell
$env:TWINE_USERNAME = "__token__"
$env:TWINE_PASSWORD = "<pypi-token>"
python -m build
python -m twine check dist/*
python -m twine upload dist/*
```

Do not commit PyPI tokens, `.pypirc`, or shell history containing tokens.
