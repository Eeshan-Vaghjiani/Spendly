# Live deployment and tester APK

## Recommended no-cost pilot architecture

- **Render Free web service:** Flask API, admin website, migrations, linear
  spending forecast, and Isolation Forest anomaly model.
- **Neon Free Postgres:** persistent users, transactions, budgets, forecasts,
  alerts, and recommendations.
- **Flutter release APK:** calls the public HTTPS Render URL. Testers do not
  need Docker, your laptop, or a USB connection.

The free deployment uses `MODEL_RUNTIME=lightweight`. This keeps the trained
multiple-linear-regression forecast and Isolation Forest live, while leaving
TensorFlow/LSTM out of the 512 MB web container. The full Docker configuration
still loads the LSTM locally or on a larger paid service. Project evaluation
already records a lower MAE for the linear model than the LSTM, so this is a
defensible pilot choice rather than an untrained replacement.

## 1. Create the Postgres database

1. Create a Neon account and a project in a region close to the Render region.
2. In **Connect**, enable the pooled connection and copy the connection string.
3. Keep it private. The app accepts the normal `postgresql://...` Neon string
   and selects Psycopg automatically.

## 2. Deploy the API and admin website

1. Put this project in a private GitHub repository. Do not commit `.env`.
2. In Render, create a **Blueprint** from the repository. `render.yaml` selects
   the lightweight Dockerfile and the Free instance.
3. Supply the prompted secret values:
   - `DATABASE_URL`: Neon pooled connection string.
   - `ADMIN_USERNAME`: a non-obvious administrator username.
   - `ADMIN_PASSWORD`: a unique password of at least 16 characters.
   - `GOOGLE_WEB_CLIENT_ID`: the Web OAuth client ID used by the Android app.
4. Deploy. The startup command runs database migrations automatically.
5. Verify `https://YOUR-SERVICE.onrender.com/api/v1/health` returns `healthy`.
6. Open `https://YOUR-SERVICE.onrender.com/admin` and enter the administrator
   credentials. Always use HTTPS; the admin page uses HTTP Basic authentication.

Render Free services sleep after 15 minutes without inbound traffic and can
take about a minute to wake. Tell testers that the first request after idle can
be slow. Neon scales idle compute to zero independently while retaining data.

## 3. Build the shareable APK

From PowerShell:

```powershell
cd mobile
.\build_tester_apk.ps1 `
  -ApiBaseUrl "https://YOUR-SERVICE.onrender.com/api/v1" `
  -GoogleWebClientId "YOUR_WEB_CLIENT_ID.apps.googleusercontent.com"
```

The shareable file is written to:

`mobile/dist/spendly-testers.apk`

The test build currently uses the Android debug signing key when no private
release keystore is configured. That is acceptable for a closed pilot shared
directly with testers, but not for Play Store publishing. Testers may need to
allow installation from the app used to open the APK.

## 4. Production cautions

- Free tiers are appropriate for a university pilot, not a guaranteed service.
- Rotate secrets if they are ever exposed and never place the Neon connection
  string or admin password in the APK.
- The administrator can see account and model-output metadata. Restrict access,
  document this in the privacy notice, and do not expose `/admin` credentials
  to testers.
- Add database backups, monitoring, email verification/password reset, admin
  audit logs, and a paid always-on API before using real financial data at
  production scale.

## Current provider references

- Render free service limits: https://render.com/docs/free
- Render Docker deployment: https://render.com/docs/docker
- Neon Free plan: https://neon.com/pricing
- Neon pooled connections: https://neon.com/docs/connect/connection-pooling
- Hugging Face Spaces overview: https://huggingface.co/docs/hub/spaces-overview
