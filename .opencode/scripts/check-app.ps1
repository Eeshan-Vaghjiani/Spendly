[CmdletBinding()]
param(
    [ValidateSet('Mobile', 'Backend', 'All', 'Doctor')]
    [string]$Suite = 'Mobile',
    [string]$Python = 'python'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$root = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$results = [System.Collections.Generic.List[object]]::new()

function Invoke-Check {
    param([string]$Name, [string]$Directory, [string]$Executable, [string[]]$Arguments)
    $code = 1
    Push-Location -LiteralPath $Directory
    try {
        Write-Host "`n[$Name] $Executable $($Arguments -join ' ')"
        $global:LASTEXITCODE = 0
        & $Executable @Arguments
        $code = $LASTEXITCODE
    }
    catch {
        Write-Warning "$Name could not run: $($_.Exception.Message)"
    }
    finally {
        Pop-Location
    }
    $results.Add([pscustomobject]@{ Check = $Name; ExitCode = $code })
}

if (-not (Test-Path -LiteralPath (Join-Path $root 'mobile/pubspec.yaml'))) {
    throw 'Expected the Spendly repository above .opencode/scripts.'
}
if ($Suite -eq 'Doctor') {
    Invoke-Check 'Flutter version' $root 'flutter' @('--version')
    Invoke-Check 'Flutter doctor' $root 'flutter' @('doctor')
    Invoke-Check 'Devices' $root 'flutter' @('devices')
    Invoke-Check 'Emulators' $root 'flutter' @('emulators')
    Invoke-Check 'Python version' $root $Python @('--version')
    Invoke-Check 'Pytest availability' $root $Python @('-m', 'pytest', '--version')
}
if ($Suite -in @('Mobile', 'All')) {
    $mobile = Join-Path $root 'mobile'
    Invoke-Check 'Flutter analyze' $mobile 'flutter' @('analyze', '--no-pub')
    # No LIVE_API_BASE_URL define: the network-writing live test remains skipped.
    Invoke-Check 'Flutter offline tests' $mobile 'flutter' @('test', '--no-pub')
}
if ($Suite -in @('Backend', 'All')) {
    # Function-scoped SQLite + fake inference; no .env loading or server startup.
    Invoke-Check 'Backend lightweight tests' $root $Python @(
        '-m', 'pytest', 'backend/tests', 'services/recommendation_engine/tests',
        '--ignore=backend/tests/test_model_inference.py',
        '--ignore=backend/tests/test_vertical_slice_real.py', '-q'
    )
}
$results | Format-Table -AutoSize
if (@($results | Where-Object ExitCode -ne 0).Count -gt 0) {
    Write-Host 'One or more checks failed or could not run. See output above.'
    exit 1
}
Write-Host 'Requested checks passed. This does not imply native-device or live-backend coverage.'
exit 0
