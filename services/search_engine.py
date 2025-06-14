import json
import logging
from pathlib import Path
import asyncio

from config.settings import USE_MOCK_DATA

logger = logging.getLogger(__name__)
MOCK_DATA_DIR = Path(__file__).resolve().parent.parent / "mocks"

def load_mock_data(filename: str) -> list[dict]:
    filepath = MOCK_DATA_DIR / filename
    if not filepath.exists():
        logger.warning(f"Mock data file not found: {filepath}")
        return []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data: list[dict] = json.load(f)
            default_marketplace = filename.split('_')[0].capitalize()
            for item in data:
                item.setdefault('marketplace', default_marketplace)
            return data
    except json.JSONDecodeError as e_json:
        logger.error(f"Error decoding JSON from {filepath}: {e_json}", exc_info=True)
        return []
    except Exception as e_load:
        logger.error(f"Error loading mock data from {filepath}: {e_load}", exc_info=True)
        return []

def filter_mock_products(products: list[dict], query: str) -> list[dict]:
    if not query:
        return products
    query_lower = query.lower()
    filtered_products = [
        item for item in products
        if (query_lower in item.get("name", "").lower() or
            query_lower in item.get("description", "").lower())
    ]
    return filtered_products

async def search_products_on_marketplaces_async(query: str) -> list[dict]:
    found_products: list[dict] = []
    if USE_MOCK_DATA:
        logger.info(f"Mock search for: '{query}'")
        await asyncio.sleep(0.3)
        wb_products = load_mock_data("wildberries_mock.json")
        ym_products = load_mock_data("yandex_market_mock.json")
        ae_products = load_mock_data("aliexpress_mock.json")
        all_raw_products = wb_products + ym_products + ae_products
        found_products = filter_mock_products(all_raw_products, query)
        logger.info(f"Found {len(found_products)} mock products for '{query}'")
    else:
        logger.warning("Real API search disabled (USE_MOCK_DATA=False).")
        found_products = []
    return found_products