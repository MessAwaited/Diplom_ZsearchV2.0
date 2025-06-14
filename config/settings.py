import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///app.db")
LOG_FILE: str = os.getenv("LOG_FILE", "logs/app.log")
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()
USE_MOCK_DATA: bool = os.getenv("USE_MOCK_DATA", "False").lower() == 'true'
PRICE_MARKUP_PERCENTAGE: float = float(os.getenv("PRICE_MARKUP_PERCENTAGE", 10.0))