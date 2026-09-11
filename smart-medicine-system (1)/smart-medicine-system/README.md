# Smart Medicine Management &amp; Reminder System with AI-Based Query Assistance

A full-stack Flask web application for organizing prescribed medicines, tracking scheduled doses, monitoring expiry dates, and querying your own saved medicine data through a controlled, database-only AI assistant.

> **Status:** Priority 1 (MVP) is fully implemented and functional. See [Future Scope](#future-scope--priority-2--3) for what's next.

---

## 1. Overview

This system helps a user:

1. Register and log in securely.
2. Add medicines from their own prescription/instructions (name, dosage, schedule, expiry, quantity, notes, optional prescription file).
3. Get reminded when a dose is due, and record it as Taken / Skipped / Remind Later.
4. See a medicine automatically marked **Missed** if no action is taken within its reminder window.
5. Get automatic expiry alerts at 30, 7, and 1 day(s) before expiry, and on the expiry date itself.
6. Browse a full dose history with filters.
7. Ask a chat-style AI assistant questions about their own saved data — never a diagnosis or medicine recommendation.
8. Search/filter/sort their medicine list.
9. See everything in a responsive, modern dashboard.

## 2. Problem Statement

People on multiple medicines — especially long-term prescriptions — commonly forget doses, lose track of when a strip or bottle expires, and have no single place to see their history of taken/missed doses. Most "medicine tracker" student projects are simple CRUD apps with no real reminder logic, no expiry intelligence, and no safe way to let a user quickly recall their own data. This project builds that missing layer.

## 3. Objectives

- Give users one place to store everything about their prescribed medicines.
- Turn schedules into real, time-aware reminders — not just a static list.
- Prevent expired medicines from going unnoticed.
- Let a user *ask* for their own data in natural language, with zero risk of the assistant inventing medical advice.
- Ship a real, runnable, well-structured Flask project — not a mockup.

## 4. Features

See the in-app pages: Dashboard, My Medicines (add/edit/delete/search/filter/sort), Schedule (Today / Week), History (filterable, paginated), Notifications (reminders, expiry alerts, missed-dose alerts), AI Assistant, Profile, Settings.

## 5. Technology Stack

**Frontend:** HTML5, CSS3, Bootstrap 5, Bootstrap Icons, vanilla JavaScript
**Backend:** Python 3, Flask, Flask-SQLAlchemy, Flask-Login, Flask-WTF (CSRF), Werkzeug (password hashing)
**Database:** SQLite via SQLAlchemy ORM (swap `DATABASE_URL` for MySQL/PostgreSQL with no code changes — pure ORM, no raw SQLite-specific SQL)
**Scheduling:** APScheduler (`BackgroundScheduler`, runs every minute) for reminder generation, missed-dose sweeping, and expiry checks
**AI:** A rule/intent-based controlled assistant (works fully offline, no external API required) — see Section 8

## 6. System Architecture

```
smart-medicine-system/
├── app.py                  # App factory, blueprint registration, scheduler, error handlers
├── config.py                # Env-driven configuration
├── requirements.txt
├── .env.example
├── seed_demo_data.py        # Optional demo-data script
├── models/                  # SQLAlchemy models (User, Medicine, MedicineSchedule, MedicineHistory, Notification)
├── routes/                  # Flask blueprints (auth, dashboard, medicines, schedule, history, notifications, assistant, profile)
├── services/                 # Business logic: reminder_service, expiry_service, notification_service, assistant_service
├── templates/                # Jinja2 templates (Bootstrap 5 based)
├── static/                   # css/style.css, js/assistant.js
├── database/                  # SQLite file lives here
└── uploads/                   # Prescription file uploads
```

Routes call **services**, services touch the **database**, templates render what services/routes hand them. No business logic lives in templates, and no raw SQL is used anywhere (pure SQLAlchemy ORM, portable to MySQL/PostgreSQL).

## 7. Database Design

| Table | Purpose |
|---|---|
| `users` | Account + hashed password + per-user settings |
| `medicines` | One row per medicine the user added |
| `medicine_schedules` | One row per daily time for a medicine (a medicine can have many) |
| `medicine_history` | One row per scheduled dose *occurrence* (Pending → Taken/Skipped/Missed) |
| `notifications` | Reminder / expiry / missed / system messages, with a `dedupe_key` to prevent duplicate alerts |

Every medicine/history/notification query is scoped by `user_id` (or by a foreign-key chain back to it) — a user can never read or modify another user's data; every route uses `filter_by(..., user_id=current_user.id)` or `.first_or_404()` on an ownership-checked query before acting on an ID from the browser.

## 8. AI Assistant Architecture &amp; Safety Boundary

**Flow:** `User Question → Intent Detection → (safety check) → Database Query → Response built only from retrieved rows`

- All factual answers are assembled **only** from the user's own database rows — nothing is invented. If data is missing, the assistant says so explicitly (e.g. *"I don't have a scheduled time for this medicine in your saved records."*) instead of guessing.
- Before any intent is processed, `services/assistant_service.py` checks the message against a list of medical-advice patterns (diagnosis requests, "which medicine should I take", dosage-change requests, symptom questions, etc.). If matched, the fixed safe-refusal response is returned immediately — the database is never even queried.
- Supported intents: `NEXT_MEDICINE`, `TODAY_MEDICINES`, `CURRENT_MEDICINE`, `MEDICINE_SCHEDULE`, `EXPIRING_MEDICINES`, `MISSED_MEDICINES`, `MEDICINE_DETAILS`, `MEDICINE_HISTORY`, `GREETING`, `UNKNOWN`, `MEDICAL_ADVICE_REQUEST`.
- The assistant works **entirely offline** with this rule/intent engine — no external AI API key is required. `AI_API_KEY` in `.env` is optional and currently unused by the MVP; it's reserved for a future enhancement (see Future Scope) and the app is fully functional without it.

**The assistant will never:** diagnose, prescribe, recommend a medicine or dosage change, tell the user to start/stop a medicine, or invent any medicine information not present in the database.

## 9. Installation (Windows)

```bat
:: 1. Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate

:: 2. Install dependencies
pip install -r requirements.txt

:: 3. Copy the example environment file and edit SECRET_KEY
copy .env.example .env

:: 4. (Optional) Load demo data
python seed_demo_data.py

:: 5. Run the app
python app.py
```

Then open **http://127.0.0.1:5000** in your browser.

### macOS / Linux

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python seed_demo_data.py   # optional
python app.py
```

## 10. Configuration

All configuration lives in environment variables (see `.env.example`), loaded via `python-dotenv`. Nothing sensitive is hard-coded.

| Variable | Required | Notes |
|---|---|---|
| `SECRET_KEY` | Yes | Used to sign session cookies |
| `DATABASE_URL` | No | Defaults to a local SQLite file; point it at MySQL/PostgreSQL to migrate |
| `AI_API_KEY` | No | Reserved for a future external-AI enhancement; app works fully without it |
| `DEFAULT_REMINDER_WINDOW` | No | Minutes before a Pending dose is swept to Missed (default 60) |
| `MAX_UPLOAD_MB` | No | Prescription upload size limit (default 5) |

## 11. Demo Credentials

Run `python seed_demo_data.py` to create:

- **Email:** `demo@smartmedicine.local`
- **Password:** `demo1234`

This creates three clearly-labeled **sample** medicines ("Medicine A/B/C (Sample)") with schedules and expiry dates set 30/7/1 day(s) out, so expiry alerts and reminders are immediately visible for demonstration. This is not real prescription data.

## 12. Testing / How to Verify Each Feature

| Feature | How to test |
|---|---|
| Registration/Login | Register with a new email; try registering the same email twice (rejected); log in with wrong password (rejected) |
| Add/Edit/Delete Medicine | Add a medicine with two schedule times; edit its dosage; delete it and confirm the modal |
| Search/Filter/Sort | On "My Medicines", search by name, filter by "Expiring Soon", sort by expiry date |
| Reminders | Add a medicine with a schedule time a couple of minutes from now; wait for the scheduler tick (runs every minute) or reload the Dashboard/Schedule page (both call the reminder service synchronously too); mark it Taken/Skipped/Remind Later |
| Missed Detection | Add a schedule with a short reminder window (e.g. 5 minutes) and a time in the past; reload the dashboard — it should flip to Missed |
| Expiry Alerts | Add a medicine expiring tomorrow; check the Notifications page for the "will expire tomorrow" alert; reload — confirm no duplicate is created |
| History Filters | Visit History, filter by "This Week" and by status "Taken"/"Missed" |
| AI Assistant — safe questions | Ask "What's my next medicine?", "What medicines do I have today?", "Which medicines are expiring soon?" |
| AI Assistant — safety boundary | Ask "What medicine should I take for a headache?" or "Should I increase my dosage?" — must get the fixed refusal message, never a recommendation |
| Authorization | Log in as two different users; confirm neither can see the other's medicines (URLs use ownership-checked queries, not raw IDs) |

## 13. Security Notes

- Passwords hashed with Werkzeug (`generate_password_hash` / `check_password_hash`), never stored or displayed in plaintext.
- All state-changing routes require `@login_required` and a valid CSRF token (Flask-WTF `CSRFProtect`, enabled globally; the AI assistant's chat endpoint sends its token via the `X-CSRFToken` header).
- All queries are scoped to `current_user.id`; ownership is re-checked server-side on every edit/delete, regardless of what ID appears in the URL.
- Prescription uploads: extension allow-list (png/jpg/jpeg/pdf), a random UUID filename (the original filename is never trusted or used for storage), a 5MB size cap, and files are stored outside any directly-executable path.
- No secrets are committed — `.env` is gitignored; `.env.example` documents what's needed.

## 14. Limitations (MVP scope)

- The AI assistant's natural-language understanding is rule/keyword-based, not a trained language model — phrasing far outside the listed example patterns may fall back to "I'm not sure I understood that."
- Browser push notifications, a calendar-style month view, and Chart.js analytics are Priority 2/3 items not yet built (see below).
- Single-user households only; no caregiver/family accounts yet.

## Future Scope (Priority 2 / 3)

**Priority 2 (should-have, next):** notification center polish + browser notifications, Chart.js dashboard analytics, improved natural-language intent detection, better mobile polish.

**Priority 3 (nice-to-have):** voice assistant, multilingual assistant, QR/barcode scanning, family/caregiver accounts, cloud sync, native mobile app, pharmacy integration, IoT smart medicine box.

These are intentionally **not implemented yet**, per the project's MVP-first development order — Priority 1 was completed and verified first.

## Author

B.Sc. Computer Science final-year project.
