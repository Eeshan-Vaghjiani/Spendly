# ✅ Your Personal Finance App is Running!

## 🎉 Status: OPERATIONAL

---

## 📊 Services Running

| Service | Status | URL | Port |
|---------|--------|-----|------|
| **MySQL Database** | ✅ Healthy | Internal | 3306 |
| **Backend API** | ✅ Healthy | http://localhost:5000/api/v1 | 5000 |
| **Models Loaded** | ✅ Ready | Forecasting v1 + Anomaly v1 | - |

---

## 🔐 Demo User Credentials

- **Email:** `demo@example.com`
- **Password:** `LocalDemoPassword123!`
- **Monthly Income:** KES 50,000

---

## 🌐 API Endpoints You Can Use

### Health Check
```bash
GET http://localhost:5000/api/v1/health
```
**Response:**
```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "database": "connected",
    "forecasting_model": "loaded",
    "anomaly_model": "loaded"
  }
}
```

### Login
```bash
POST http://localhost:5000/api/v1/auth/login
Content-Type: application/json

{
  "email": "demo@example.com",
  "password": "LocalDemoPassword123!"
}
```

### Get Transactions (Requires Auth Token)
```bash
GET http://localhost:5000/api/v1/transactions
Authorization: Bearer <your_token>
```

### Create Transaction
```bash
POST http://localhost:5000/api/v1/transactions
Authorization: Bearer <your_token>
Content-Type: application/json

{
  "transaction_timestamp": "2026-07-29T14:00:00",
  "amount": 2500,
  "category": "food",
  "transaction_type": "expense",
  "merchant": "Carrefour Supermarket",
  "is_recurring": false
}
```

### Get Forecast (7-day spending prediction)
```bash
GET http://localhost:5000/api/v1/analytics/forecast
Authorization: Bearer <your_token>
```

### Get Anomalies (Unusual transactions)
```bash
GET http://localhost:5000/api/v1/analytics/anomalies
Authorization: Bearer <your_token>
```

---

## 🧪 Testing with Postman or Thunder Client

### 1. **Login First:**
- Method: `POST`
- URL: `http://localhost:5000/api/v1/auth/login`
- Body (JSON):
```json
{
  "email": "demo@example.com",
  "password": "LocalDemoPassword123!"
}
```
- Copy the `access_token` from response

### 2. **Add Transactions:**
- Method: `POST`
- URL: `http://localhost:5000/api/v1/transactions`
- Headers:
  - `Authorization: Bearer <paste_your_token_here>`
  - `Content-Type: application/json`
- Body:
```json
{
  "transaction_timestamp": "2026-07-29T10:00:00",
  "amount": 1500,
  "category": "transport",
  "transaction_type": "expense",
  "merchant": "Uber",
  "is_recurring": false
}
```

### 3. **Get Forecast:**
- Method: `GET`
- URL: `http://localhost:5000/api/v1/analytics/forecast`
- Headers: `Authorization: Bearer <your_token>`

---

## 📱 Mobile App (Flutter)

To test the mobile app:

```powershell
cd mobile
flutter pub get
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:5000/api/v1
```

**For Android Emulator:** Use `http://10.0.2.2:5000`
**For iOS Simulator:** Use `http://127.0.0.1:5000`
**For Physical Device:** Use your computer's IP address `http://192.168.x.x:5000`

---

## 🔧 Useful Commands

### View Logs
```powershell
# All services
docker compose logs -f

# Just backend
docker compose logs -f backend

# Last 50 lines
docker compose logs --tail=50 backend
```

### Check Service Status
```powershell
docker compose ps
```

### Restart Services
```powershell
# Restart backend only
docker compose restart backend

# Restart everything
docker compose restart
```

### Stop Services
```powershell
# Stop but keep data
docker compose stop

# Stop and remove containers (keeps data volumes)
docker compose down

# Stop and remove everything including data
docker compose down -v
```

### Access Backend Shell
```powershell
docker compose exec backend bash
```

### Access MySQL Shell
```powershell
docker compose exec mysql mysql -u root -p
# Password: From .env file (MYSQL_ROOT_PASSWORD)
```

---

## 🐛 Troubleshooting

### Backend Not Responding?
```powershell
# Check logs
docker compose logs backend

# Restart backend
docker compose restart backend
```

### Database Connection Error?
```powershell
# Check MySQL is healthy
docker compose ps mysql

# Should show "healthy"
# If not, restart
docker compose restart mysql
```

### "Port 5000 already in use"?
```powershell
# Find process using port 5000
netstat -ano | findstr :5000

# Kill it (replace <PID> with actual number)
taskkill /PID <PID> /F

# Then restart
docker compose up -d
```

---

## 🚀 Next Steps

1. **Test API with Postman/Thunder Client**
   - Import the endpoints above
   - Login to get token
   - Create some transactions
   - Test forecasting and anomaly detection

2. **Run Mobile App**
   - `cd mobile`
   - `flutter run`
   - Login with demo credentials
   - Test the UI

3. **Train New Models (Optional)**
   - `python scripts\run_training_pipeline.py --mode quick`
   - Generates updated LSTM and Isolation Forest models

4. **Review Model Performance**
   - Check `reports/` folder for visualizations
   - Look at `artifacts/` for model metrics

---

## 📚 Project Documentation

- **API Documentation:** Check `backend/` folder for route definitions
- **Model Documentation:** See `models/` folder for architecture details
- **Data Pipeline:** Read `README_DATA_PIPELINE.md`
- **Development Guide:** Read `README_DEVELOPMENT.md`

---

## ✅ Current Status Summary

✅ Docker Desktop: **Running**
✅ MySQL Database: **Healthy**
✅ Backend API: **Operational**
✅ Models: **Loaded** (Forecasting v1 + Anomaly v1)
✅ Demo User: **Created** (demo@example.com)
✅ Health Check: **Passing**

**🎯 Your app is ready to use!**

---

## 📞 Quick Commands Cheat Sheet

```powershell
# Start everything
docker compose up -d

# Stop everything
docker compose down

# View logs
docker compose logs -f

# Check status
docker compose ps

# Restart
docker compose restart

# Access backend shell
docker compose exec backend bash

# Run migrations
docker compose exec backend python -m flask --app backend.run:app db upgrade --directory backend/migrations

# Seed data
docker compose exec backend python backend/seed.py
```

---

**Last Updated:** 2026-07-29
**API Version:** v1
**Model Versions:** Forecasting v1, Anomaly v1
