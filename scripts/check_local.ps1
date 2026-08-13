param(
    [switch]$SkipInstall,
    [switch]$Showcase
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$VenvDir = Join-Path $RepoRoot ".venv"
$Python = Join-Path $VenvDir "Scripts\python.exe"

function Invoke-Step {
    param(
        [string]$Name,
        [scriptblock]$Command
    )

    Write-Host ""
    Write-Host "==> $Name" -ForegroundColor Cyan
    & $Command
}

Push-Location $RepoRoot
try {
    if (-not (Test-Path $Python)) {
        Invoke-Step "Create local virtual environment" {
            if (Get-Command py -ErrorAction SilentlyContinue) {
                & py -3 -m venv $VenvDir
            }
            else {
                & python -m venv $VenvDir
            }
        }
    }

    if (-not $SkipInstall) {
        Invoke-Step "Install this checkout in editable dev mode" {
            & $Python -m pip install -e ".[dev]"
        }
    }

    Invoke-Step "Compile Python sources" {
        & $Python -m compileall src scripts examples tests -q
    }

    Invoke-Step "Run Ruff critical checks" {
        & $Python -m ruff check src scripts examples tests
    }

    Invoke-Step "Run test suite" {
        & $Python -m pytest tests -q
    }

    Invoke-Step "Run release-readiness smoke check" {
        & $Python scripts\check_release_readiness.py
    }

    if (Test-Path "schemas\benchmark_submission.schema.json") {
        Invoke-Step "Validate benchmark submission schema JSON" {
            & $Python -m json.tool schemas\benchmark_submission.schema.json | Out-Null
        }
    }

    if (Test-Path "schemas\demo_artifact_contract.schema.json") {
        Invoke-Step "Validate demo artifact contract schema JSON" {
            & $Python -m json.tool schemas\demo_artifact_contract.schema.json | Out-Null
        }
    }

    if (Test-Path "examples\benchmark_submissions\example_redacted_submission.json") {
        Invoke-Step "Validate example benchmark submission" {
            & $Python scripts\validate_benchmark_submission.py examples\benchmark_submissions\example_redacted_submission.json
        }
    }

    if (Test-Path "docs\demo_artifacts.yaml") {
        Invoke-Step "Validate demo artifact contract" {
            & $Python scripts\validate_demo_artifacts.py
        }
    }

    if (Test-Path "notebooks\tradearena_5min_colab.ipynb") {
        Invoke-Step "Validate Colab notebook JSON" {
            & $Python -m json.tool notebooks\tradearena_5min_colab.ipynb | Out-Null
        }
    }

    if ($Showcase) {
        Invoke-Step "Regenerate showcase index from existing artifacts" {
            & $Python scripts\run_showcase.py --reuse-existing
        }
    }

    Invoke-Step "Check git diff whitespace" {
        & git diff --check
    }

    Write-Host ""
    Write-Host "Local check passed for $RepoRoot" -ForegroundColor Green
}
finally {
    Pop-Location
}
