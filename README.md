# Expense Tracker API + Flutter Client

## Backend Auth (JWT)

- Register: `POST /auth/register`
- Login: `POST /auth/login`
- Refresh: `POST /auth/refresh`
- Logout: `POST /auth/logout`
- Current user: `GET /auth/me`

Protected endpoints now derive identity from bearer JWT:

- `GET /expenses`
- `POST /expenses`
- `POST /chat`

## Migrations (Alembic)

Run migrations before starting the API:

```bash
alembic upgrade head
```

## Railway Environment Variables

- `DATABASE_URL`
- `JWT_SECRET`
- `JWT_ALGORITHM` (default `HS256`)
- `ACCESS_TOKEN_MINUTES` (default `30`)
- `REFRESH_TOKEN_DAYS` (default `14`)
- `GOOGLE_CLOUD_PROJECT_ID` / `CES_APP_ID` / `CES_LOCATION` (if chat/CES enabled)
- `GOOGLE_APPLICATION_CREDENTIALS` or `GOOGLE_CREDENTIALS_JSON` (if needed)

## Flutter App

The Flutter client is in `flutter_app/` and uses:

- `flutter_secure_storage` for token persistence
- `dio` with refresh-on-401 interceptor
- `flutter_riverpod` for auth state

Run with API base URL:

```bash
flutter run --dart-define=API_BASE_URL=https://your-api-url
```
