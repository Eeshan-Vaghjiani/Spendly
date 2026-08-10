# Development Guide

## 1. Python and model setup

Use Python 3.10:

```powershell
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Validate and train:

```powershell
python scripts\run_training_pipeline.py --mode quick
```

Full mode uses the larger configured network and epoch limit with the currently
validated model-ready dataset:

```powershell
python scripts\run_training_pipeline.py --mode full
```

Versioned artefacts are written below `artifacts/models/`.

## 2. Environment and MySQL

Copy `.env.example` to `.env` and replace every placeholder with strong,
distinct values. `.env` is not committed.

Start MySQL and Flask:

```powershell
docker compose up --build -d
```

The backend becomes available at:

```text
http://localhost:5000/api/v1
```

Apply the migration manually when needed:

```powershell
docker compose exec backend python -m flask --app backend.run:app db upgrade --directory backend/migrations
```

The backend startup script already applies pending migrations before Gunicorn
starts.

Optional development seed:

```powershell
docker compose exec backend python backend/seed.py
```

Preview the configured retention purge, then apply it explicitly if the
preview is correct:

```powershell
docker compose exec backend python -m flask --app backend.run:app purge-retained-data
docker compose exec backend python -m flask --app backend.run:app purge-retained-data --apply
```

`DATA_RETENTION_DAYS=0` disables retention eligibility.

## 3. Backend tests

```powershell
python -m pytest backend\tests services\recommendation_engine\tests -q
```

## 4. Flutter

```powershell
cd mobile
flutter pub get
flutter analyze
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:5000/api/v1
```

For Flutter tests:

```powershell
flutter test
flutter test --dart-define=LIVE_API_BASE_URL=http://127.0.0.1:5000/api/v1
```

The second command runs the live Flutter API test and therefore requires the
Docker backend to be healthy.

`10.0.2.2` routes from the Android Emulator to the development computer.

## 5. Complete local workflow

1. Validate/train models.
2. Configure `.env`.
3. Run `docker compose up --build`.
4. Verify `GET http://localhost:5000/api/v1/health`.
5. Run Flutter with the emulator backend URL.
6. Register, enter or upload at least eight weeks of transactions, create a
   budget, and run analysis.
