# Moscow Hotel — Secure Admin Version

## What changed
- Guests can use the hotel website and submit bookings.
- Booking data is stored in SQLite.
- `/admin` and `/bookings` are protected by an administrator login.
- Unauthenticated visitors are redirected to `/admin/login`.
- Admin logout clears the session.
- For production, set `ADMIN_USERNAME`, `ADMIN_PASSWORD`, and `SECRET_KEY` as environment variables.

## Local login
Default demo credentials:
- Username: `admin`
- Password: `Moscow@123`

Change these before public deployment.

## Run
```powershell
python -m pip install -r requirements.txt
python app.py
```

Website: http://127.0.0.1:5000

Admin login: http://127.0.0.1:5000/admin/login

Admin dashboard: http://127.0.0.1:5000/admin

## Production
Use:
```bash
gunicorn app:app
```
Set environment variables on the hosting platform:
- SECRET_KEY = a long random secret
- ADMIN_USERNAME = your private admin username
- ADMIN_PASSWORD = a strong private password

Do not commit `.venv` or `moscow_hotel.db` to GitHub.
