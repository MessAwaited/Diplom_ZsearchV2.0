import flet as ft
from views.main_view import MainView
import logging
import os
from pathlib import Path
from views.theme_config import apply_theme
from database.models import create_db_and_tables
from config.settings import LOG_FILE, LOG_LEVEL, USE_MOCK_DATA

CRITICAL_ERROR_COLOR = "#D32F2F"

def setup_logging():
    log_dir = Path(LOG_FILE).parent
    if not log_dir.exists():
        try:
            log_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e_log_dir:
            print(f"Error creating log directory {log_dir}: {e_log_dir}")

    try:
        logging.basicConfig(
            level=LOG_LEVEL,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)",
            handlers=[
                logging.FileHandler(LOG_FILE, encoding='utf-8'),
                logging.StreamHandler()
            ],
        )
    except Exception as e_basicConfig:
        print(f"Error setting up logging with basicConfig: {e_basicConfig}")
        logging.basicConfig(level=LOG_LEVEL, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    logging.getLogger("flet_core").setLevel(logging.WARNING)
    logging.getLogger("flet_runtime").setLevel(logging.WARNING)
    logging.getLogger("watchfiles").setLevel(logging.WARNING)
    logging.getLogger("websockets").setLevel(logging.WARNING)
    logging.getLogger("flet").setLevel(logging.INFO)

def main(page: ft.Page):
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("===================================")
    logger.info("Application starting...")
    if USE_MOCK_DATA:
        logger.info("----- RUNNING IN MOCK DATA MODE -----")
    else:
        logger.warning("----- RUNNING WITHOUT MOCK DATA (API calls would be expected) -----")

    try:
        apply_theme(page)
        logger.info("Theme applied successfully.")
    except KeyError as e_theme:
        logger.critical(f"Failed to apply theme due to missing key: {e_theme}", exc_info=True)
        page.bgcolor = ft.Colors.GREY_200  
        logger.warning("Using fallback background color due to theme error.")
        page.add(ft.Text(f"Ошибка темы: отсутствует ключ {e_theme}. Используется цвет по умолчанию.", color=CRITICAL_ERROR_COLOR, size=16))
    except Exception as e_theme:
        logger.critical(f"Failed to apply theme: {e_theme}", exc_info=True)
        page.bgcolor = ft.Colors.GREY_200 
        logger.warning("Using fallback background color due to theme error.")
        page.add(ft.Text(f"Критическая ошибка темы: {e_theme}", color=CRITICAL_ERROR_COLOR, size=16))

    page.window_width = 1280
    page.window_height = 800
    page.window_min_width = 800
    page.window_min_height = 600
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    try:
        create_db_and_tables()
        logger.info("Database tables checked/created successfully.")
    except Exception as e_db:
        logger.critical(f"CRITICAL: Failed to create/check database tables: {e_db}", exc_info=True)
        page.controls.clear()
        page.add(ft.Text(f"Критическая ошибка инициализации БД: {e_db}. Проверьте файл логов.", color=CRITICAL_ERROR_COLOR, size=16))
        page.update()
        return

    try:
        main_app_view = MainView(page)
        page.controls.clear()  
        page.add(main_app_view.build())  
        logger.info("MainView instance created and added to page.")
    except Exception as e_main_view:
        logger.critical(f"CRITICAL: Failed to initialize or add MainView: {e_main_view}", exc_info=True)
        page.controls.clear()
        page.add(ft.Text(f"Критическая ошибка UI: {e_main_view}. Проверьте логи.", color=CRITICAL_ERROR_COLOR, size=16))
        page.update()
        return

    page.update()
    logger.info("Application UI initialized and page updated. Application is running.")

if __name__ == "__main__":
    if not os.path.exists(".env"):
        print("WARNING: .env file not found. Using default settings specified in config/settings.py.")
        print("For custom settings (like DATABASE_URL or disabling MOCK_DATA), please create .env file from .env.example.")
    
    ft.app(target=main)