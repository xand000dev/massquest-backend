# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Activate the virtualenv (Windows)
venv\Scripts\activate

# Run dev server
python manage.py runserver

# Create and apply migrations
python manage.py makemigrations
python manage.py migrate

# Run tests
python manage.py test

# Run a single test module
python manage.py test game.tests.test_game_engine
```

## Stack

| Layer | Technology |
|-------|-----------|
| Web framework | Django 5.2 + Django REST Framework |
| Database | SQLite (dev) / PostgreSQL via psycopg2 (prod) |
| Task queue | Celery + Redis |
| Bot integration | python-telegram-bot |

## Architecture

```
massquest/          # Django project config (settings, root URLs, wsgi)
game/               # Single Django app holding all game logic
  models.py         # CharacterProfile, DailyLog, FoodEntry
  game_engine.py    # Stateless GameEngine service class (pure logic, no HTTP)
  serializers.py    # DRF serializers for CharacterProfile and DailyLog
  views.py          # APIView subclasses wired to game_engine.py
  urls.py           # Mounted at root in massquest/urls.py
  migrations/       # Auto-generated migration files
```

### Key design decisions

- **`GameEngine` is stateless** — all methods are `@staticmethod` or `@classmethod`. Views are the only place that call `profile.save()` directly outside of `GameEngine` methods that explicitly document their own saves.
- **`CharacterProfile` is the single source of truth** for RPG state (`level`, `xp`, `hp`). `DailyLog` rows are used only for weight history lookups inside `check_level_up`.
- **Level-up trigger**: weight increased ≥ 1 kg vs. the most recent prior log that has `weight_logged` set.
- **HP penalty trigger**: called externally (e.g. a Celery beat task) — not triggered automatically from views. If HP hits 0, the character loses one level and HP is restored to `max_hp`.

### Rank thresholds (defined in `game_engine.RANKS`)

| Levels | Rank |
|--------|------|
| 0–5 | Novice |
| 6–10 | Warrior |
| 11–20 | Titan |
| 21+ | God |

## API endpoints

All endpoints require authentication (`IsAuthenticated`).

| Method | Path | Description |
|--------|------|-------------|
| POST | `/log-calories/` | `{ "calories": int }` → awards XP |
| POST | `/log-weight/` | `{ "weight": float }` → may trigger level-up |
| GET | `/status/` | Returns character stats + rank name |
