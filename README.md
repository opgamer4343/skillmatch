# SkillMatch — Skill Matching & Internship Finder

Full-stack Django application connecting students with real internships posted by companies.

## What was fixed in this release

| Bug | Fix |
|---|---|
| Company/Dashboard views used hardcoded mock data | Replaced ALL mock functions with real ORM queries |
| Internship post/edit didn't save to DB | `InternshipForm.save()` now sets `company=request.user` and commits |
| Applicant CV download returned fake 404 paths | Real `StudentCV` / `StudentProfile.resume` lookup with ownership check |
| `AppRegistryNotReady` crash on startup | Signals moved inside `_connect_signals()` called from `NotificationsConfig.ready()` |
| `company/apps.py` typo `default_auto_auto_field` | Fixed to `default_auto_field` |
| `requirements.txt` missing packages | Added `whitenoise`, `django-celery-results`, `django-environ` |
| Stale context processors in settings | Removed non-existent `dashboard.context_processors`, `company.context_processors` |
| All internship cards used static/fake data | Students now see only real listings posted by companies |
| Match % was hardcoded | Computed live: `student_score vs threshold - 2pt buffer` |
| Applicants sorted by hardcoded rank | Sorted by real `overall_score DESC` from `AssessmentAttempt` |
| Old Bootstrap-only frontend | New unified CSS (`skillmatch.css`) with sidebar layout |

## Quick Start

```bash
# 1. Clone and install
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env — add GEMINI_API_KEY at minimum

# 3. Run migrations
python manage.py migrate

# 4. Create admin user
python manage.py createsuperuser

# 5. Start the app
python manage.py runserver

# 6. (Optional) Celery for background tasks
celery -A config worker -l info
celery -A config beat -l info
```

## User Flow

### Company
1. Register at `/accounts/register/company/`
2. Verify email OTP
3. Post internships at `/company/internships/post/`
4. View real applicants sorted by assessment score at `/company/applicants/`
5. Schedule interviews — meeting link required for video, location for onsite

### Student
1. Register at `/accounts/register/`
2. Verify email OTP
3. Browse **real** internships posted by companies at `/dashboard/internships/`
4. Apply directly — cover letter optional
5. Take skill assessment at `/assessment/` (Gemini AI generates questions + course recs)
6. Track applications and interview status

## Environment Variables

See `.env.example` for all variables. Minimum required for local dev:
- `GEMINI_API_KEY` — Google Gemini API key for AI features
- All others have safe defaults (SQLite, console email, etc.)

## Key Architecture

```
accounts/     Custom User (student/company) + profiles + OTP auth
company/      Internship, Application, Interview models + company dashboard
dashboard/    Student dashboard — all data from real DB
assessment/   Skill test (Gemini AI) + score history + CV generation
notifications/ In-app + email notifications via Celery signals
api/          DRF + JWT token endpoints
```


## Google Meet interview setup

1. Install the new dependencies from `requirements.txt`.
2. Run migrations:
   - `python manage.py migrate`
3. Add these environment variables:
   - `GOOGLE_OAUTH_CLIENT_ID`
   - `GOOGLE_OAUTH_CLIENT_SECRET`
   - `GOOGLE_OAUTH_REDIRECT_URI`
   - `SITE_URL`
4. In Google Cloud Console, enable Google Calendar API and add the redirect URI.
5. Start Redis and Celery so 1-hour reminders are sent on time.
6. As a company user, open Company Settings and connect Google Calendar.
7. Schedule a video interview with `Auto-create Google Meet link` enabled.

When Google is connected, SkillMatch will create a Google Calendar event, store the Meet link, and include the same link in reminder emails.
