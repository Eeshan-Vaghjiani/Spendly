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
$normalizedClientId = $GoogleWebClientId.Trim()
if (-not $normalizedClientId.EndsWith(".apps.googleusercontent.com")) {
    throw "GoogleWebClientId must be a Web OAuth client ID ending in .apps.googleusercontent.com."
}

$mobileRoot = $PSScriptRoot
$outputDirectory = Join-Path $mobileRoot "dist"
New-Item -ItemType Directory -Path $outputDirectory -Force | Out-Null

Push-Location $mobileRoot
try {
    flutter pub get
    flutter build apk --release `
        --dart-define="API_BASE_URL=$normalizedUrl" `
        --dart-define="GOOGLE_WEB_CLIENT_ID=$normalizedClientId"
    $builtApk = Join-Path $mobileRoot "build\app\outputs\flutter-apk\app-release.apk"
    $testerApk = Join-Path $outputDirectory "spendly-testers.apk"
    Copy-Item -LiteralPath $builtApk -Destination $testerApk -Force
    Write-Host "Tester APK ready: $testerApk"
}
finally {
    Pop-Location
}
