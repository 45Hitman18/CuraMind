# CuraMind AI

CuraMind AI is a Django-based healthcare workflow platform for patients, doctors, and admins.

## Features

- Role-based authentication (`patient`, `doctor`, `admin`)
- Patient portal for records, appointments, messages, and scan upload
- Doctor dashboard with review workflow, reports, appointments, and profile
- Admin dashboard with user management, system logs, settings, and audit tracking
- Immutable audit logs for key actions

## Project Structure

- `manage.py` – Django entrypoint
- `curamind_ai/` – project settings and root URLs
- `accounts/` – authentication, role-based user model
- `patients/` – patient views and messaging
- `doctors/` – doctor dashboards, review flow, reports
- `records/` – medical record model, upload and review state
- `appointments/` – appointment scheduling/approval
- `audit/` – audit logs and admin reporting
- `templates/` – HTML templates
- `media/` – uploaded files

## Requirements

See `requirements.txt`.

## Setup

1. Create and activate virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Install dependencies

```powershell
pip install -r requirements.txt
```

3. Apply migrations

```powershell
python manage.py migrate
```

4. (Optional) Create superuser

```powershell
python manage.py createsuperuser
```

5. Run server

```powershell
python manage.py runserver
```

Then open: `http://127.0.0.1:8000/`

## Common Commands

- Run checks:

```powershell
python manage.py check
```

- Make migrations:

```powershell
python manage.py makemigrations
```

- Apply migrations:

```powershell
python manage.py migrate
```

## Notes

- This project currently uses SQLite (`db.sqlite3`) for local development.
- Uploaded scan files are stored under `media/medical_records/`.
- For production, use a proper WSGI/ASGI server and secure environment configuration.
