# Flutter Mobile App Guide

The Flutter Android project is under `mobile/`.

## Architecture

- `presentation/`: screens, widgets, and Riverpod controllers
- `domain/`: repository contract
- `data/`: typed models, API repository, HTTP client, secure token storage
- `core/`: environment and shared network errors

## Screens

Splash, registration, login, dashboard, manual transaction entry, transaction
history, CSV upload, budget management, forecast detail, unusual-spending
alerts, recommendations, analysis history, and profile/settings are included.

## Backend URL

Android Emulator cannot reach the host through `localhost`. The default is:

```text
http://10.0.2.2:5000/api/v1
```

Override it at build/run time:

```powershell
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:5000/api/v1
```

For a physical device, use the computer's reachable LAN address and configure
the backend firewall/CORS appropriately.

## Run

```powershell
cd mobile
flutter pub get
flutter run
```

## Test

```powershell
flutter analyze
flutter test
```

The application includes loading, empty, error, retry, input-validation,
responsive-layout, and accessible-label behaviour. Tokens are stored through
`flutter_secure_storage`.
