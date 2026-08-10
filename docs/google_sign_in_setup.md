# Google Sign-In setup for Spendly

This app should use Google only to prove the user's identity. The Flask backend
must verify Google's ID token and then return the same Spendly JWT used
by email/password login. Never trust a Google user ID or email sent by the app
without verifying the ID token.

## 1. Create the Google OAuth clients

In Google Cloud Console, configure the OAuth consent screen and create both:

1. An **Android client** with package name
   `com.evagh.capstone.spending_support` and the SHA-1 of the signing certificate.
2. A **Web application client** for the Flask backend. Copy its client ID; this
   is the `serverClientId` used by Flutter and the audience checked by Flask.

For development, get the debug SHA-1 with:

```powershell
cd mobile\android
.\gradlew signingReport
```

After enabling Play App Signing, also add the SHA-1 shown in **Play Console →
Setup → App integrity**. Debug, upload, and Play signing certificates have
different fingerprints.

References: [Google Android OAuth client setup](https://codelabs.developers.google.com/sign-in-with-google-android#4),
[Play signing certificate fingerprints](https://developers.google.com/android/guides/client-auth).

## 2. Flutter implementation

The app uses `google_sign_in` 7.x and initializes the current plugin API with
the **Web client ID**:

```dart
final googleSignIn = GoogleSignIn.instance;

await googleSignIn.initialize(
  serverClientId: const String.fromEnvironment('GOOGLE_WEB_CLIENT_ID'),
);
```

Follow the package's authentication-event flow, obtain the signed-in account's
ID token, and send it to `POST /api/v1/auth/google`. Do not place a client secret
in the Flutter app. The Android implementation requires the correct package,
signing SHA, and `serverClientId`.

Reference: [official Flutter `google_sign_in` package](https://pub.dev/packages/google_sign_in),
[Android plugin configuration](https://pub.dev/packages/google_sign_in_android).

Run the app with:

```powershell
flutter run `
  --dart-define=API_BASE_URL=http://10.0.2.2:5000/api/v1 `
  --dart-define=GOOGLE_WEB_CLIENT_ID=YOUR_WEB_CLIENT_ID.apps.googleusercontent.com
```

## 3. Flask verification

The `google-auth` dependency and `/api/v1/auth/google` endpoint are included.
Store the Web client ID in the backend environment as
`GOOGLE_WEB_CLIENT_ID`. The endpoint:

1. Read `id_token` from the JSON body.
2. Call `google.oauth2.id_token.verify_oauth2_token(...)` with the Web client ID
   as the expected audience.
3. Require a verified email and use Google's stable `sub` claim as the external
   identity key.
4. Find or create the local user, then issue the app's normal access token.
5. Return the same `{access_token, user}` response shape as `/auth/login`.

Minimal verification core:

```python
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

claims = id_token.verify_oauth2_token(
    token_from_mobile,
    google_requests.Request(),
    current_app.config["GOOGLE_WEB_CLIENT_ID"],
)
if not claims.get("email_verified"):
    raise ApiError("INVALID_GOOGLE_TOKEN", "Google email is not verified.", 401)

google_subject = claims["sub"]
email = claims["email"]
display_name = claims.get("name") or email.split("@", 1)[0]
```

Google recommends sending an ID token over HTTPS, verifying its signature,
audience, issuer, and expiry, then creating the application's own session.
Reference: [Google backend authentication](https://developers.google.com/identity/sign-in/android/backend-auth).

## 4. Current status

The repository, controller, backend endpoint, migration, and **Continue with
Google** button are implemented. The button remains disabled in builds that do
not supply `GOOGLE_WEB_CLIENT_ID`. Complete the Android/Web OAuth clients and
test both debug- and release-signed builds before distributing the APK.
