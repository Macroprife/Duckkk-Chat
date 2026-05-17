"""Duck Chat 🦆 — FastAPI proxy for Ollama / OpenClaw with PostgreSQL persistence.

Entry point — delegates to `app.create_app()`.
"""

import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
# Quiet prometheus client's noisy logger
logging.getLogger("prometheus_client").setLevel(logging.WARNING)

from duckapp import create_app

app = create_app()
