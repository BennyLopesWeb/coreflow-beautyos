#!/bin/sh
set -e

if echo "$DATABASE_URL" | grep -q "^mysql"; then
  echo "⏳ Aguardando MySQL..."
  until python -c "
import os, sys, time
from sqlalchemy import create_engine, text
url = os.environ.get('DATABASE_URL', '')
for i in range(30):
    try:
        e = create_engine(url)
        with e.connect() as c:
            c.execute(text('SELECT 1'))
        sys.exit(0)
    except Exception:
        time.sleep(2)
sys.exit(1)
"; do
    echo "MySQL indisponível — retry em 2s..."
    sleep 2
  done
  echo "✅ MySQL pronto"
  alembic upgrade head
fi

exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
