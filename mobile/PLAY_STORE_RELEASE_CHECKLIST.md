# Play Store release checklist

## Completed in the project

- Branded launcher icon, in-app logo, Flutter splash, and Android 12 splash.
- Production internet permission and user-facing app name.
- Backups disabled for local financial data.
- Accessible Material 3 theme with readable contrast and 48+ dp controls.
- Simplified forecast, spending-check, and recommendation output.
- Static analysis, widget/API tests, and backend tests.
- Release APK compilation and APK Signature Scheme v2 verification.
- Gradle generated a 44.0 MB release bundle and `jarsigner` verified its
  archive signature. The local bundle still uses the debug certificate.
- Optional secure release-signing configuration through
  `android/key.properties`.

## Required before the first upload

1. Deploy the Flask API behind HTTPS and build with the real URL:

   ```powershell
   flutter build appbundle --release `
     --dart-define=API_BASE_URL=https://YOUR_DOMAIN/api/v1
   ```

2. Install **Android SDK Command-line Tools (latest)** in Android Studio's SDK
   Manager, run `flutter doctor --android-licenses`, and confirm that
   `flutter doctor -v` reports a healthy Android toolchain. The current machine
   generated the AAB but Flutter could not run its final native-symbol check
   because `cmdline-tools` is missing.
3. Create an upload keystore, copy `android/key.properties.example` to
   `android/key.properties`, and fill in the real values. Never upload a bundle
   signed with the debug key.
4. Confirm that `com.evagh.capstone.spending_support` is the final package name.
   It cannot be changed after publishing.
5. Host a public privacy policy and add its URL to the Play Console and the app.
6. Complete Play Console's Data safety, financial-features, content-rating,
   target-audience, ads, and app-access forms truthfully.
7. Add the Play App Signing SHA-1 to the Google Android OAuth client if Google
   Sign-In is enabled.
8. Replace the generated demo screenshots with screenshots from the final
   Play-signed build using realistic, non-sensitive sample data.
9. Run an internal test track on at least one small phone, one modern phone,
   Android 12+, slow/offline network, and large accessibility text.

## Final commands

```powershell
cd mobile
dart analyze lib test
flutter test
flutter build appbundle --release `
  --dart-define=API_BASE_URL=https://YOUR_DOMAIN/api/v1
```

The upload artifact is `build/app/outputs/bundle/release/app-release.aab`.
