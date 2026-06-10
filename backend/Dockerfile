FROM python:3.12-slim

WORKDIR /app

# Install the exact dependency set the app runs with today (pinned from the
# working venv) — includes fastapi + uvicorn (not declared in pyproject).
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App source (agents/, tools/, core/, techniques/, main.py, ...).
COPY . .

# Cloud Run injects $PORT; default 8080 for local container runs.
ENV PORT=8080
CMD ["sh", "-c", "exec uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
