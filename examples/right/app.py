"""Main application entry point."""

import logging
import sys

from models.user import User

logger = logging.getLogger(__name__)


def create_app(*, debug: bool = False):
    """Initialize and return the application."""
    logging.basicConfig(level=logging.DEBUG if debug else logging.INFO)
    logger.info("Starting application v2")
    return {"name": "demo-app", "version": "2.0.0", "debug": debug}


def handle_request(path: str, method: str = "GET"):
    """Route an incoming request to the appropriate handler."""
    logger.debug("Handling %s %s", method, path)

    if path == "/":
        return {"status": 200, "body": "Welcome to Demo App"}
    if path == "/users":
        users = [User("Alice", "alice@example.com", role="admin")]
        return {"status": 200, "body": [u.to_dict() for u in users]}
    if path.startswith("/users/"):
        user_id = path.split("/")[-1]
        return {"status": 200, "body": {"id": user_id}}

    logger.warning("Route not found: %s", path)
    return {"status": 404, "body": "Not found"}


if __name__ == "__main__":
    app = create_app()
    print(f"Running {app['name']} v{app['version']}")
    sys.exit(0)
