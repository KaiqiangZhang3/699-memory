# taskservice

A small task-management service: JSON over HTTP, session-cookie login, a service layer, and SQLite storage. Python standard library only.

## Run the tests

```bash
python -m pytest -q
```

## Run the server

```bash
python -m app.server --db tasks.db --port 8000 --seed
```

## Layout

- `app/web.py`: WSGI routes (`/login`, `/logout`, `/tasks`, `/tasks/<id>`, `/health`)
- `app/auth.py`: users, password hashing, sessions
- `app/services/`: task operations and access rules
- `app/db.py`: SQLite schema and connection
- `tests/`: pytest suite
