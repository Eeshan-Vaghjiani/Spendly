param(
    [Parameter(Mandatory = $true)]
    [string]$ApiBaseUrl,

    [Parameter(Mandatory = $true)]
    [string]$GoogleWebClientId
)

$ErrorActionPreference = "Stop"
$normalizedUrl = $ApiBaseUrl.TrimEnd('/')
if (-not $normalizedUrl.StartsWith("https://")) {
    throw "Tester builds require an HTTPS API URL."
}
if (-not $normalizedUrl.EndsWith("/api/v1")) {
    throw "ApiBaseUrl must end with /api/v1."
}
if ($normalizedUrl -match 'example\.com|YOUR[-_]|localhost|127\.0\.0\.1') {
    throw "A real hosted API URL is required, not a placeholder or loopback address."
}
$normalizedClientId = $GoogleWebClientId.Trim()
if (-not $normalizedClientId.EndsWith(".apps.googleusercontent.com")) {
    throw "GoogleWebClientId must be a Web OAuth client ID ending in .apps.googleusercontent.com."
}
if ($normalizedClientId -notmatch '^\d+-[a-z0-9]+\.apps\.googleusercontent\.com$') {
    throw "Supply the real public Web OAuth client ID, not a placeholder."
}

$mobileRoot = $PSScriptRoot
$outputDirectory = Join-Path $mobileRoot "dist"
New-Item -ItemType Directory -Path $outputDirectory -Force | Out-Null

# Read only the SDK path; never read or print signing-key passwords.
$localProperties = Join-Path $mobileRoot "android\local.properties"
$sdkLine = Get-Content -LiteralPath $localProperties | Where-Object { $_ -like 'sdk.dir=*' } | Select-Object -First 1
if (-not $sdkLine) { throw "Android SDK path is missing from local.properties." }
$sdkRoot = $sdkLine.Substring(8).Replace('\\', '\')
$buildTools = Get-ChildItem -LiteralPath (Join-Path $sdkRoot 'build-tools') -Directory |
    Where-Object { $_.Name -match '^\d+\.\d+\.\d+$' } |
    Sort-Object { [version]$_.Name } -Descending | Select-Object -First 1
if (-not $buildTools) { throw "Android build tools are required to verify the APK." }
$signer = Join-Path $buildTools.FullName 'apksigner.bat'
$aapt = Join-Path $buildTools.FullName 'aapt.exe'

function Get-ApkIdentity([string]$ApkPath) {
    $certificate = & $signer verify --print-certs $ApkPath
    if ($LASTEXITCODE -ne 0) { throw "APK signature verification failed: $ApkPath" }
    $certText = $certificate -join "`n"
    $fingerprints = [regex]::Matches($certText, 'certificate SHA-256 digest: ([a-f0-9]+)') |
        ForEach-Object { $_.Groups[1].Value }
    $badging = & $aapt dump badging $ApkPath
    if ($LASTEXITCODE -ne 0) { throw "APK manifest inspection failed: $ApkPath" }
    $match = [regex]::Match(($badging -join "`n"), "package: name='([^']+)' versionCode='(\d+)' versionName='([^']+)'")
    if (-not $match.Success -or -not $fingerprints) { throw "Could not verify APK identity." }
    return [ordered]@{
        package = $match.Groups[1].Value
        version_code = [int]$match.Groups[2].Value
        version_name = $match.Groups[3].Value
        signing_certificate_sha256 = ($fingerprints -join ',')
    }
}

Push-Location $mobileRoot
try {
    flutter pub get
    if ($LASTEXITCODE -ne 0) { throw "Dependency resolution failed. Existing tester APK was not replaced." }
    flutter build apk --release `
        --dart-define="API_BASE_URL=$normalizedUrl" `
        --dart-define="GOOGLE_WEB_CLIENT_ID=$normalizedClientId"
    if ($LASTEXITCODE -ne 0) { throw "Release build failed. Existing tester APK was not replaced." }
    $builtApk = Join-Path $mobileRoot "build\app\outputs\flutter-apk\app-release.apk"
    $testerApk = Join-Path $outputDirectory "spendly-testers.apk"
    $identity = Get-ApkIdentity $builtApk
    $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    $backup = $null
    if (Test-Path -LiteralPath $testerApk) {
        $previous = Get-ApkIdentity $testerApk
        if ($identity.package -ne $previous.package -or $identity.signing_certificate_sha256 -ne $previous.signing_certificate_sha256) {
            throw "Package or signing identity changed. Refusing to replace the existing tester APK."
        }
        if ($identity.version_code -le $previous.version_code) {
            throw "Increase pubspec.yaml versionCode above $($previous.version_code) before replacing the tester APK."
        }
        $backup = Join-Path $outputDirectory "spendly-testers-backup-$($previous.version_name)-$stamp-$([guid]::NewGuid().ToString('N').Substring(0,8)).apk"
        Copy-Item -LiteralPath $testerApk -Destination $backup
    }
    $versionedApk = Join-Path $outputDirectory "spendly-$($identity.version_name)-$($identity.version_code).apk"
    if (Test-Path -LiteralPath $versionedApk) { throw "Versioned APK already exists: $versionedApk. Use a new build number." }
    Copy-Item -LiteralPath $builtApk -Destination $versionedApk
    Copy-Item -LiteralPath $builtApk -Destination $testerApk -Force
    $hash = (Get-FileHash -LiteralPath $testerApk -Algorithm SHA256).Hash.ToLowerInvariant()
    $manifest = [ordered]@{
        built_at = (Get-Date).ToUniversalTime().ToString('o')
        identity = $identity
        api_base_url = $normalizedUrl
        google_web_client_id = $normalizedClientId
        sha256 = $hash
        previous_apk_backup = $backup
        backend_release_required = '1.3.0 (migrations through 0006_alert_reviews; selected portable LSTM)'
        backend_deployed_by_this_script = $false
    }
    $manifest | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $outputDirectory 'spendly-release-manifest.json') -Encoding utf8
    Write-Host "Tester APK ready: $testerApk"
    Write-Host "Versioned APK: $versionedApk"
    Write-Host "SHA-256: $hash"
    Write-Host "Previous APK retained: $backup"
    Write-Host "Deploy backend release 1.3.0 before distributing this APK. This script does not deploy the server."
}
finally {
    Pop-Location
}
