# 🚀 How to Start Your Personal Finance App

## Prerequisites Check

Before running, make sure you have:
- ✅ Docker Desktop installed and **RUNNING**
- ✅ Python installed
- ✅ Flutter installed (for mobile app)

---

## Step 1: Start Docker Desktop

**You need to start Docker Desktop first!**

1. Open Docker Desktop application on Windows
2. Wait until it shows "Docker Desktop is running"
3. You should see the whale icon in your system tray

---

## Step 2: Start Backend + Database

Once Docker Desktop is running, open PowerShell in this directory and run:

```powershell
# Start all services (MySQL + Backend)
docker compose up --build -d
```

**Wait 30-60 seconds** for services to start, then:

```powershell
# Run database migrations
docker compose exec backend python -m flask --app backend.run:app db upgrade --directory backend/migrations

# Seed initial data
docker compose exec backend python backend/seed.py
```

### Verify Backend is Running:

Open browser: http://localhost:5000/api/v1/health

You should see: `{"status": "healthy"}`

---

## Step 3: Run Mobile App (Optional)

If you want to test the Flutter mobile app:

```powershell
cd mobile
flutter pub get
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:5000/api/v1
```

---

## Step 4: Train Models (Optional)

If you want to retrain the ML models:

```powershell
# Quick training (faster)
python scripts\run_training_pipeline.py --mode quick

# Full training (more accurate)
python scripts\run_training_pipeline.py --mode full
```

---

## 🛑 How to Stop

```powershell
# Stop all services
docker compose down

# Stop and remove all data (clean slate)
docker compose down -v
```

---

## 📊 Useful Commands

### View Logs:
```powershell
# All services
docker compose logs -f

# Just backend
docker compose logs -f backend

# Just database
docker compose logs -f mysql
```

### Check Running Services:
```powershell
docker compose ps
```

### Access Backend Shell:
```powershell
docker compose exec backend bash
```

### Access MySQL:
```powershell
docker compose exec mysql mysql -u root -p
# Password is in your .env file (MYSQL_ROOT_PASSWORD)
```

---

## 🐛 Troubleshooting

### Problem: "Docker is not running"
**Solution:** Open Docker Desktop and wait for it to start

### Problem: "Port 5000 already in use"
**Solution:**
```powershell
# Find what's using port 5000
netstat -ano | findstr :5000

# Kill the process (replace PID with actual number)
taskkill /PID <PID> /F
```

### Problem: Backend won't start
**Solution:** Check logs:
```powershell
docker compose logs backend
```

### Problem: Database connection error
**Solution:** Make sure MySQL is healthy:
```powershell
docker compose ps
# mysql should show "healthy"
```

---

## 📱 API Endpoints

Once running, you can test these endpoints:

- **Health Check:** http://localhost:5000/api/v1/health
- **API Docs:** http://localhost:5000/api/v1/docs (if Swagger is configured)

---

## ✅ Quick Start Checklist

- [ ] Docker Desktop is running
- [ ] Run: `docker compose up --build -d`
- [ ] Wait 30 seconds
- [ ] Run: `docker compose exec backend python -m flask --app backend.run:app db upgrade --directory backend/migrations`
- [ ] Run: `docker compose exec backend python backend/seed.py`
- [ ] Test: Open http://localhost:5000/api/v1/health
- [ ] Should see: `{"status": "healthy"}`
- [ ] ✅ App is running!
