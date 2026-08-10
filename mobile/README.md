# Spendly mobile app

Flutter client for personal spending forecasts, simple next-step recommendations,
and unusual-spending checks.

## Forecast learning stages

- Weeks 1-7 use a personal rolling-spending baseline and show data readiness.
- At week 8, the saved LSTM and its better-performing linear comparator are
  blended, with more weight given to the comparator based on held-out metrics.
- Readiness is not presented as accuracy. Actual accuracy is calculated only
  after a forecast week ends and the user has recorded that week's expenses.
- The saved model is experimental and was validated on synthetic development
  data; the app displays that limitation to users.

Registration requires acceptance of the service terms and essential data use.
Future de-identified model-improvement permission is a separate optional choice.

## Run locally

```powershell
flutter pub get
flutter run `
  --dart-define=API_BASE_URL=http://10.0.2.2:5000/api/v1 `
  --dart-define=GOOGLE_WEB_CLIENT_ID=YOUR_WEB_CLIENT_ID.apps.googleusercontent.com
```

Use `10.0.2.2` for the Android emulator, `127.0.0.1` for an iOS simulator,
or your computer's LAN address for a physical device.

## Verify

```powershell
dart analyze lib test
flutter test
flutter build appbundle --release `
  --dart-define=API_BASE_URL=https://api.example.com/api/v1 `
  --dart-define=GOOGLE_WEB_CLIENT_ID=YOUR_WEB_CLIENT_ID.apps.googleusercontent.com
```

Replace the example API URL with the deployed HTTPS backend before a real
release. See [PLAY_STORE_RELEASE_CHECKLIST.md](PLAY_STORE_RELEASE_CHECKLIST.md)
and [Google Sign-In setup](../docs/google_sign_in_setup.md).
