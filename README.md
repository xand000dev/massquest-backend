# MassQuest

> A gamified calorie tracker RPG built for hardgainers who need more than a spreadsheet to stay consistent.

Log your food. Gain XP. Level up when the scale moves. Miss a day — lose HP. Simple enough to use daily, brutal enough to keep you honest.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | Django 5.2 + Django REST Framework |
| Auth | DRF Token Authentication |
| Database | SQLite (dev) · PostgreSQL via psycopg2 (prod) |
| Task Queue | Celery 5 + Redis |
| Config | python-decouple |

---

## Quick Start

```bash
# 1. Clone
git clone https://github.com/xand000dev/massquest.git
cd massquest

# 2. Virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Dependencies
pip install -r requirements.txt

# 4. Environment
cp .env.example .env
# Edit .env and set SECRET_KEY at minimum

# 5. Database
python manage.py migrate

# 6. (Optional) Seed a test user — username: xand / password: test123
python manage.py seed_test_user

# 7. Run
python manage.py runserver
```

**Celery (optional, required for midnight HP penalty):**
```bash
celery -A massquest worker -l info   # terminal 1
celery -A massquest beat -l info     # terminal 2
```

---

## API Endpoints

All endpoints require `Authorization: Token <token>`.

| Method | Endpoint | Body | Description |
|---|---|---|---|
| `POST` | `/api-token-auth/` | `{username, password}` | Get auth token |
| `POST` | `/log-calories/` | `{calories: int}` | Log food intake, earn XP |
| `POST` | `/log-weight/` | `{weight: float}` | Log weight in kg, may trigger level-up |
| `GET` | `/status/` | — | View character stats + rank |

**Example — log 600 calories:**
```bash
curl -X POST http://localhost:8000/log-calories/ \
  -H "Authorization: Token <your_token>" \
  -H "Content-Type: application/json" \
  -d '{"calories": 600}'
```
```json
{
  "calories_eaten_today": 600,
  "xp_gained": 60,
  "total_xp": 60
}
```

---

## Game Mechanics

### XP
Every calorie logged converts to XP:
```
XP = calories ÷ 10
```
600 kcal → 60 XP.

### Level Up
Logging a weight that is **≥ 1 kg heavier** than your previous recorded weight triggers a level-up.

### HP Penalty (runs at 23:59 UTC via Celery beat)
Miss a day of logging and you take **−20 HP**. Hit 0 HP and you **lose a level** — HP resets to max. A warning fires when HP drops below 40.

### Ranks

| Levels | Rank |
|---|---|
| 1–5 | Novice |
| 6–10 | Warrior |
| 11–20 | Titan |
| 21+ | God |

---

## Environment Variables

See `.env.example` for all variables. Required:

| Variable | Description |
|---|---|
| `SECRET_KEY` | Django secret key |
| `DEBUG` | `True` for development |
| `DATABASE_URL` | PostgreSQL URL (prod) |
| `REDIS_URL` | Redis URL for Celery |

---

![Built with Claude Code](https://img.shields.io/badge/Built%20with-Claude%20Code-black?style=for-the-badge&logo=anthropic)
