"""Legacy configuration module — scheduled for removal."""

DATABASE_URL = "sqlite:///local.db"
SECRET_KEY = "dev-secret-key-change-me"
SESSION_TIMEOUT = 3600
MAX_RETRIES = 3

FEATURES = {
    "dark_mode": False,
    "notifications": True,
    "analytics": False,
}
