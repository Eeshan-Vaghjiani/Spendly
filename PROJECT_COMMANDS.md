# Project Commands

## Models

```powershell
python scripts\run_training_pipeline.py --mode quick
python scripts\run_training_pipeline.py --mode full
```

## Backend and MySQL

```powershell
docker compose up --build -d
docker compose exec backend python -m flask --app backend.run:app db upgrade --directory backend/migrations
docker compose exec backend python backend/seed.py
docker compose exec backend python -m flask --app backend.run:app purge-retained-data
docker compose exec backend python -m flask --app backend.run:app purge-retained-data --apply
```

The backend startup script applies pending migrations automatically. The
explicit migration command is provided for maintenance and verification.

Backend URL: `http://localhost:5000/api/v1`

## Backend tests

```powershell
python -m pytest
```

## Flutter

```powershell
cd mobile
flutter pub get
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:5000/api/v1
flutter test
flutter test --dart-define=LIVE_API_BASE_URL=http://127.0.0.1:5000/api/v1
```

## Data validation only

```powershell
python scripts\validate_model_data.py
```
