"""Main application entry point."""

import logging
import os
import sys

from models.user import User

logger = logging.getLogger(__name__)

DEBUG = os.getenv("DEBUG", "false").lower() == "true"


def create_app():
    """Initialize and return the application."""
    logging.basicConfig(level=logging.DEBUG if DEBUG else logging.INFO)
    logger.info("Starting application")
    return {"name": "demo-app", "version": "1.0.0", "debug": DEBUG}


def handle_request(path: str, method: str = "GET"):
    """Route an incoming request to the appropriate handler."""
    logger.debug("Handling %s %s", method, path)

    if path == "/":
        return {"status": 200, "body": "Welcome"}
    if path == "/users":
        users = [User("Alice", "alice@example.com")]
        return {"status": 200, "body": [u.to_dict() for u in users]}

    return {"status": 404, "body": "Not found"}


if __name__ == "__main__":
    app = create_app()
    print(f"Running {app['name']} v{app['version']}")
    sys.exit(0)
