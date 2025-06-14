import flet as ft
import logging
import asyncio
import bcrypt
from datetime import datetime

from database.session import get_user_data_by_username, add_user, save_user_query, get_user_queries
from services.search_engine import search_products_on_marketplaces_async
from services.recommendations import get_recommendations
from utils.helpers import create_product_card, create_price_chart, calculate_dynamic_price, predict_demand_simple
from utils.export_data import export_products_to_csv
from views.theme_config import APP_THEME_COLORS
from config.settings import PRICE_MARKUP_PERCENTAGE

logger = logging.getLogger(__name__)

class MainView(ft.Control):
    def __init__(self, page: ft.Page):
        super().__init__()
        self.page = page
        self.current_user_data: dict | None = None
        self.search_results_data: list[dict] = []
        self.products_to_compare: list[dict] = []

    
        self.username_field = ft.TextField(
            label="Имя пользователя", width=300, border_radius=8,
            border_color=APP_THEME_COLORS.get("border_color"),
            focused_border_color=APP_THEME_COLORS.get("primary"),
            text_style=ft.TextStyle(color=APP_THEME_COLORS.get("on_surface")),
            on_submit=self._focus_password
        )
        self.password_field = ft.TextField(
            label="Пароль", password=True, can_reveal_password=True, width=300,
            border_radius=8, border_color=APP_THEME_COLORS.get("border_color"),
            focused_border_color=APP_THEME_COLORS.get("primary"),
            text_style=ft.TextStyle(color=APP_THEME_COLORS.get("on_surface")),
            on_submit=self._on_login_submit
        )

        self.query_field = ft.TextField(
            label="Поиск товаров...", expand=True, border_radius=8,
            border_color=APP_THEME_COLORS.get("border_color"),
            focused_border_color=APP_THEME_COLORS.get("primary"),
            prefix_icon=ft.Icons.SEARCH,
            text_style=ft.TextStyle(color=APP_THEME_COLORS.get("on_surface")),
            on_submit=self._on_search_submit
        )
        self.search_button = ft.ElevatedButton(
            text="Найти", icon=ft.Icons.SEARCH,
            on_click=self._on_search_submit,
            bgcolor=APP_THEME_COLORS.get("primary"),
            color=APP_THEME_COLORS.get("on_primary"),
            height=40, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8))
        )
        self.loading_indicator = ft.ProgressRing(
            visible=False, width=24, height=24,
            color=APP_THEME_COLORS.get("primary"), stroke_width=3
        )
        self.results_column_cards = ft.ResponsiveRow(
            spacing=12, run_spacing=12,
            alignment=ft.MainAxisAlignment.START,
            vertical_alignment=ft.CrossAxisAlignment.START
        )
        self.results_info_text = ft.Text(
            "", size=16, weight=ft.FontWeight.BOLD,
            color=APP_THEME_COLORS.get("primary")
        )
        self.recommendations_container = ft.Column(
            spacing=10, visible=False, alignment=ft.MainAxisAlignment.START
        )
        self.price_chart_container = ft.Container(
            border_radius=8, padding=ft.padding.all(10), visible=False,
            bgcolor=APP_THEME_COLORS.get("surface")
        )

        self.compare_list_view = ft.ListView(expand=False, spacing=5, height=180, visible=False)
        self.compare_panel_action_button = ft.ElevatedButton(
            "Сравнить выбранные", icon=ft.Icons.COMPARE_ARROWS,
            on_click=self.show_comparison_dialog_event,
            visible=False,
            bgcolor=APP_THEME_COLORS.get("secondary"),
            color=APP_THEME_COLORS.get("on_primary"),
            height=35, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8))
        )
        self.compare_panel_content_column = ft.Column([
            ft.Text("Товары для сравнения:", weight=ft.FontWeight.BOLD, color=APP_THEME_COLORS.get("on_surface")),
            self.compare_list_view,
            self.compare_panel_action_button
        ], spacing=8)
        self.compare_panel = ft.Container(
            self.compare_panel_content_column,
            visible=False, padding=ft.padding.all(10), border_radius=8,
            bgcolor=APP_THEME_COLORS.get("surface_opacity_005"),
            border=ft.Border(bottom=ft.BorderSide(1, APP_THEME_COLORS.get("border_color"))),
            margin=ft.margin.only(bottom=10),
            shadow=ft.BoxShadow(blur_radius=5, color=APP_THEME_COLORS.get("black_with_opacity_85", "#000000D9"))
        )

        self.login_button_form = ft.ElevatedButton(
            "Войти", width=145, on_click=self._on_login_submit,
            bgcolor=APP_THEME_COLORS.get("primary"),
            color=APP_THEME_COLORS.get("on_primary"), height=40,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8))
        )
        self.register_button_form = ft.TextButton(
            "Регистрация", on_click=self._on_register_submit,
            style=ft.ButtonStyle(color=APP_THEME_COLORS.get("primary"))
        )
        self.login_form_container = self._create_login_form_container()

        
        self.overlay_content = ft.Container(
            visible=False,
            bgcolor=ft.Colors.BLACK54,  
            alignment=ft.alignment.center,
            expand=True,
            content=ft.Column(
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=10
            )
        )

        self._main_interface_instance: ft.Column | None = None

    def _create_login_form_container(self) -> ft.Container:
        login_form_items = [
            ft.Row([
                ft.Icon(name=ft.Icons.BUBBLE_CHART, size=40, color=APP_THEME_COLORS.get("primary")),
                ft.Text("Zsearch AI", size=32, weight=ft.FontWeight.BOLD, font_family="Roboto", color=APP_THEME_COLORS.get("on_surface"))
            ], alignment=ft.MainAxisAlignment.CENTER, spacing=10),
            ft.Text("Вход в систему аналитики", size=18, color=APP_THEME_COLORS.get("text_secondary"), text_align=ft.TextAlign.CENTER),
            self.username_field,
            self.password_field,
            ft.Row([self.login_button_form, self.register_button_form], alignment=ft.MainAxisAlignment.CENTER, spacing=15, width=300),
        ]
        return ft.Container(
            content=ft.Column(login_form_items, alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=20),
            width=400, padding=ft.padding.symmetric(vertical=40, horizontal=30), border_radius=12,
            bgcolor=APP_THEME_COLORS.get("surface"),
            shadow=ft.BoxShadow(spread_radius=2, blur_radius=15, color=APP_THEME_COLORS.get("black_with_opacity_85", "#0000001A"), offset=ft.Offset(0, 5))
        )

    def _create_main_interface_instance(self) -> ft.Stack:
        if not self.current_user_data:
            logger.error("Attempted to create main interface without user data.")
            return ft.Stack([ft.Column([ft.Text("Ошибка: нет данных пользователя.", color=APP_THEME_COLORS.get("error"))])])

        export_csv_button = ft.IconButton(
            icon=ft.Icons.DOWNLOAD, tooltip="Экспорт в CSV",
            on_click=self._on_export_csv_submit,
            icon_color=APP_THEME_COLORS.get("primary"), icon_size=22
        )
        header_content_left = ft.Row([
            ft.Icon(name=ft.Icons.PERSON_OUTLINE, color=APP_THEME_COLORS.get("primary")),
            ft.Text(f"{self.current_user_data['username']}", weight=ft.FontWeight.BOLD, size=16, color=APP_THEME_COLORS.get("on_surface"))
        ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER)
        header_content_right = ft.Row([
            ft.IconButton(icon=ft.Icons.HISTORY, tooltip="История запросов", on_click=self._on_history_submit, icon_color=APP_THEME_COLORS.get("primary"), icon_size=22),
            export_csv_button,
            ft.IconButton(icon=ft.Icons.LOGOUT, tooltip="Выход", on_click=self._on_logout_submit, icon_color=APP_THEME_COLORS.get("error", ft.Colors.RED_500), icon_size=22),
        ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER)
        header_row = ft.Container(
            padding=ft.padding.symmetric(horizontal=20, vertical=10),
            bgcolor=APP_THEME_COLORS.get("surface"),
            border=ft.Border(bottom=ft.BorderSide(1, APP_THEME_COLORS.get("border_color"))),
            content=ft.Row(
                [header_content_left, header_content_right],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER
            )
        )
        search_bar_row = ft.Row(
            [self.query_field, self.search_button, self.loading_indicator],
            spacing=15, vertical_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER
        )
        content_area = ft.Column(
            [
                self.results_info_text,
                self.price_chart_container,
                self.recommendations_container,
                self.compare_panel,
                ft.Container(content=self.results_column_cards, expand=True, padding=ft.padding.only(top=15))
            ],
            scroll=ft.ScrollMode.ADAPTIVE, expand=True, spacing=15
        )
        main_content = ft.Column(
            [header_row, ft.Container(search_bar_row, padding=ft.padding.all(20)), content_area],
            expand=True, spacing=0, alignment=ft.MainAxisAlignment.START,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH
        )
        return ft.Stack([main_content, self.overlay_content], expand=True)

    def build(self):
        logger.info(f"BUILD CALLED. current_user_data is {'set' if self.current_user_data else 'None'}")
        if self.current_user_data:
            if not self._main_interface_instance:
                self._main_interface_instance = self._create_main_interface_instance()
            return self._main_interface_instance
        else:
            self.username_field.value = ""
            self.password_field.value = ""
            self.username_field.error_text = None
            self.password_field.error_text = None
            return ft.Container(
                content=self.login_form_container,
                alignment=ft.alignment.center,
                expand=True
            )

    def update(self):
        self.page.update()

    def _focus_password(self, _e: ft.ControlEvent | None = None):
        self.password_field.focus()
        self.update()

    def _on_login_submit(self, e: ft.ControlEvent | None = None):
        logger.info("Login button clicked or Enter pressed in password field")
        self.page.run_task(self.login_event)

    async def login_event(self, _e: ft.ControlEvent | None = None):
        username = self.username_field.value.strip() if self.username_field.value else ""
        password = self.password_field.value if self.password_field.value else ""

        self.username_field.error_text = None
        self.password_field.error_text = None
        has_error = False

        if not username:
            self.username_field.error_text = "Введите имя пользователя"
            has_error = True
        if not password:
            self.password_field.error_text = "Введите пароль"
            has_error = True

        if has_error:
            self.update()
            return

        logger.info(f"Login attempt for user: {username}")
        user_data = get_user_data_by_username(username)

        if user_data:
            logger.info(f"User data found for {username}: ID {user_data.get('id')}")
            stored_password_hash = user_data.get("password_hash", "")
            password_ok = False
            if stored_password_hash:
                try:
                    password_ok = bcrypt.checkpw(password.encode('utf-8'), stored_password_hash.encode('utf-8'))
                    logger.info(f"Password check for {username}: {'OK' if password_ok else 'Failed'}")
                except ValueError as ve:
                    logger.error(f"bcrypt.checkpw ValueError for user {username}: {ve}")
                except Exception as ex_bcrypt:
                    logger.error(f"Unexpected bcrypt error for user {username}: {ex_bcrypt}", exc_info=True)

            if password_ok:
                self.current_user_data = user_data
                self._show_snackbar(f"Добро пожаловать, {self.current_user_data['username']}!", APP_THEME_COLORS.get("success"))
                self._main_interface_instance = self._create_main_interface_instance()
                self.page.controls.clear()
                self.page.add(self._main_interface_instance)
                self.page.update()
                logger.info("Main interface loaded after successful login")
            else:
                self._show_snackbar("Неверный логин или пароль.", APP_THEME_COLORS.get("error"))
                self.password_field.error_text = " "
                self.username_field.error_text = "Неверные данные"
        else:
            logger.info(f"Login failed: User not found - {username}")
            self._show_snackbar("Неверный логин или пароль.", APP_THEME_COLORS.get("error"))
            self.password_field.error_text = " "
            self.username_field.error_text = "Неверные данные"

        self.update()

    def _on_register_submit(self, e: ft.ControlEvent | None = None):
        logger.info("Register button clicked")
        self.page.run_task(self.register_event)

    async def register_event(self, _e: ft.ControlEvent | None = None):
        username = self.username_field.value.strip() if self.username_field.value else ""
        password = self.password_field.value if self.password_field.value else ""
        self.username_field.error_text = None
        self.password_field.error_text = None
        has_error = False

        if not username or len(username) < 3:
            self.username_field.error_text = "Имя должно быть не короче 3 символов"
            has_error = True
        if not password or len(password) < 6:
            self.password_field.error_text = "Пароль должен быть не короче 6 символов"
            has_error = True

        if has_error:
            self.update()
            return

        logger.info(f"Registration attempt for user: {username}")
        if get_user_data_by_username(username):
            self.username_field.error_text = "Это имя пользователя уже занято"
            self._show_snackbar("Пользователь с таким именем уже существует.", APP_THEME_COLORS.get("error"))
        else:
            try:
                if add_user(username, password):
                    self._show_snackbar("Регистрация прошла успешно! Теперь вы можете войти.", APP_THEME_COLORS.get("success"))
                    self.username_field.value = ""
                    self.password_field.value = ""
                else:
                    self._show_snackbar("Произошла ошибка при регистрации. Попробуйте еще раз.", APP_THEME_COLORS.get("error"))
            except Exception as ex_add_user:
                logger.error(f"Unexpected error during user registration: {ex_add_user}", exc_info=True)
                self._show_snackbar(f"Непредвиденная ошибка регистрации: {ex_add_user}", APP_THEME_COLORS.get("error"))
        self.update()

    def _on_logout_submit(self, e: ft.ControlEvent | None = None):
        logger.info("Logout button clicked")
        self.page.run_task(self.logout_event)

    async def logout_event(self, _e: ft.ControlEvent | None = None):
        logger.info(f"User '{self.current_user_data.get('username') if self.current_user_data else 'Unknown'}' logging out.")
        self.current_user_data = None
        self.search_results_data = []
        self.products_to_compare = []
        self.query_field.value = ""
        self.results_column_cards.controls.clear()
        self.results_info_text.value = ""
        self.recommendations_container.controls.clear()
        self.recommendations_container.visible = False
        self.price_chart_container.content = None
        self.price_chart_container.visible = False
        self.compare_panel.visible = False
        self.overlay_content.visible = False
        self.update_compare_panel_display()
        self._main_interface_instance = None
        self._show_snackbar("Вы успешно вышли из системы.", APP_THEME_COLORS.get("success"))
        self.page.controls.clear()
        self.page.add(self._create_login_form_container())
        self.page.update()

    def _show_snackbar(self, message: str, bgcolor: str):
        if not self.page:
            logger.error("Page reference (self.page) is not set in MainView. Cannot show snackbar.")
            return

        self.page.snack_bar = ft.SnackBar(
            content=ft.Text(message, color=APP_THEME_COLORS.get("on_primary", ft.Colors.WHITE)),
            bgcolor=bgcolor,
            open=True,
            duration=3000
        )
        self.page.update()

    def _on_search_submit(self, e: ft.ControlEvent | None = None):
        logger.info("Search button clicked or Enter pressed in query field")
        self.page.run_task(self.handle_search_query_event)

    async def handle_search_query_event(self, _e: ft.ControlEvent | None = None):
        logger.info("Handling search query event")
        await self.execute_search()

    async def execute_search(self, query_override: str | None = None):
        if not self.current_user_data:
            self._show_snackbar("Пожалуйста, войдите в систему.", APP_THEME_COLORS.get("error"))
            logger.warning("Search attempted without user login")
            return

        query = query_override if query_override is not None else self.query_field.value.strip()
        self.query_field.error_text = None
        if not query:
            self.query_field.error_text = "Введите поисковый запрос."
            self.update()
            logger.warning("Search attempted with empty query")
            return

        self.loading_indicator.visible = True
        self.search_button.disabled = True
        self.results_column_cards.controls.clear()
        self.recommendations_container.controls.clear()
        self.recommendations_container.visible = False
        self.price_chart_container.visible = False
        self.price_chart_container.content = None
        self.results_info_text.value = "Идет поиск..."
        self.overlay_content.visible = False
        self.update()
        logger.info(f"Starting search for query: '{query}'")

        try:
            user_id = self.current_user_data.get('id')
            if user_id:
                save_user_query(user_id, query)
                logger.info(f"User query '{query}' saved for user_id: {user_id}")
            else:
                logger.warning("Cannot save user query, user_id not found in current_user_data.")

            self.search_results_data = await search_products_on_marketplaces_async(query)
            logger.info(f"Search results: {len(self.search_results_data)} items found")

            if not self.search_results_data:
                self.results_info_text.value = f"По запросу '{query}' ничего не найдено."
                logger.info(f"No results found for query: '{query}'")
            else:
                self.results_info_text.value = f"Найдено товаров: {len(self.search_results_data)}"
                new_cards_controls = []
                for product_item in self.search_results_data:
                    is_compared = any(
                        p_comp.get('id') == product_item.get('id') and
                        p_comp.get('marketplace') == product_item.get('marketplace')
                        for p_comp in self.products_to_compare
                    )
                    card_control = create_product_card(
                        product_item,
                        on_details_click=lambda p_data=product_item: self.page.run_task(self.show_product_details_event, p_data),
                        on_compare_click=self.toggle_compare_product_event,
                        is_compared=is_compared,
                        theme_colors=APP_THEME_COLORS
                    )
                    new_cards_controls.append(ft.Column([card_control], col={"xs": 12, "sm": 6, "md": 4, "lg": 3, "xl": 2.4}))
                self.results_column_cards.controls = new_cards_controls
                logger.info(f"Added {len(new_cards_controls)} product cards to UI.")

                chart_control = create_price_chart(self.search_results_data, APP_THEME_COLORS)
                if isinstance(chart_control, ft.Control):
                    self.price_chart_container.content = chart_control
                    self.price_chart_container.visible = True
                    logger.info("Price chart added to UI.")

                recommendations = get_recommendations(self.search_results_data, query, top_n=4)
                search_results_ids = {(p.get('id'), p.get('marketplace')) for p in self.search_results_data}
                filtered_recommendations = [
                    rec_item for rec_item in recommendations
                    if (rec_item.get('id'), rec_item.get('marketplace')) not in search_results_ids
                ]
                logger.info(f"Recommendations generated: {len(recommendations)} items, filtered to {len(filtered_recommendations)} unique items.")

                if filtered_recommendations:
                    self.recommendations_container.controls.append(
                        ft.Text("Рекомендуем также:", weight=ft.FontWeight.BOLD, size=16, color=APP_THEME_COLORS.get("primary"))
                    )
                    rec_row_items_controls = []
                    for rec_item in filtered_recommendations:
                        is_rec_compared = any(
                            p_comp.get('id') == rec_item.get('id') and
                            p_comp.get('marketplace') == rec_item.get('marketplace')
                            for p_comp in self.products_to_compare
                        )
                        rec_card = create_product_card(
                            rec_item,
                            on_details_click=lambda p_data=rec_item: self.page.run_task(self.show_product_details_event, p_data),
                            on_compare_click=self.toggle_compare_product_event,
                            is_compared=is_rec_compared,
                            theme_colors=APP_THEME_COLORS
                        )
                        rec_row_items_controls.append(ft.Column([rec_card], col={"xs": 12, "sm": 6, "md": 4, "lg": 3}))
                    if rec_row_items_controls:
                        self.recommendations_container.controls.append(
                            ft.ResponsiveRow(rec_row_items_controls, spacing=10, run_spacing=10, alignment=ft.MainAxisAlignment.START)
                        )
                        logger.info(f"Added {len(rec_row_items_controls)} recommendation cards to UI.")
                    self.recommendations_container.visible = True
                else:
                    self.recommendations_container.visible = False
                    logger.info("No unique recommendations to display after filtering.")
        except Exception as ex_search:
            logger.error(f"Search execution error: {ex_search}", exc_info=True)
            self.results_info_text.value = "Произошла ошибка во время поиска."
            self._show_snackbar(f"Ошибка поиска: {ex_search}", APP_THEME_COLORS.get("error"))
            self.search_results_data = []
        finally:
            self.loading_indicator.visible = False
            self.search_button.disabled = False
            self.update()
            logger.info("Search completed and UI updated.")

    def _on_history_submit(self, e: ft.ControlEvent | None = None):
        """Синхронный обработчик для истории."""
        logger.info("History button clicked")
        self.page.run_task(self.show_history_event)

    async def show_history_event(self, _e: ft.ControlEvent | None = None):
        logger.info(f"show_history_event called. User: {self.current_user_data}")
        if not self.current_user_data:
            self._show_snackbar("Пожалуйста, войдите, чтобы увидеть историю.", APP_THEME_COLORS.get("error"))
            return

        user_id = self.current_user_data.get('id')
        if not user_id:
            logger.error("User ID is missing in current_user_data for history.")
            self._show_snackbar("Ошибка: ID пользователя не найден.", APP_THEME_COLORS.get("error"))
            return

        queries = get_user_queries(user_id)
        logger.info(f"Retrieved history queries for user_id {user_id}: {queries}")

        if not queries:
            self._show_snackbar("История запросов пуста.", APP_THEME_COLORS.get("secondary"))
            return

        history_items = [
            ft.ListTile(
                title=ft.Text(q_text, color=APP_THEME_COLORS.get("on_surface")),
                leading=ft.Icon(name=ft.Icons.HISTORY, color=APP_THEME_COLORS.get("primary")),
                on_click=lambda _event, query_val=q_text: self.page.run_task(self._search_from_history, query_val),
                dense=True,
                hover_color=APP_THEME_COLORS.get("primary_opacity_01", "#1DB9541A")
            ) for q_text in queries
        ]

        dialog_content = ft.Container(
            content=ft.Column([
                ft.Text("История запросов", weight=ft.FontWeight.BOLD, color=APP_THEME_COLORS.get("primary")),
                ft.Column(history_items, scroll=ft.ScrollMode.ADAPTIVE, spacing=2),
                ft.TextButton("Закрыть", on_click=self.close_overlay_event, style=ft.ButtonStyle(color=APP_THEME_COLORS.get("primary")))
            ], spacing=10),
            bgcolor=APP_THEME_COLORS.get("surface"),
            border_radius=10,
            padding=ft.padding.all(15),
            width=350,
            height=300,
            shadow=ft.BoxShadow(blur_radius=10, color=APP_THEME_COLORS.get("black_with_opacity_85", "#000000D9"))
        )

        self.overlay_content.content.controls = [dialog_content]
        self.overlay_content.visible = True
        self.page.update()
        logger.info("History overlay opened.")

    async def _search_from_history(self, query: str):
        logger.info(f"Searching from history: query '{query}'")
        self.query_field.value = query
        self.close_overlay_event()
        await asyncio.sleep(0.05)
        await self.execute_search(query_override=query)

    def close_overlay_event(self, _e: ft.ControlEvent | None = None):
        self.overlay_content.visible = False
        self.overlay_content.content.controls = []
        self.page.update()
        logger.info("Overlay closed via close_overlay_event.")

    async def show_product_details_event(self, product: dict):
        logger.info(f"show_product_details_event called for product: {product.get('name')}")
        markup_percentage = PRICE_MARKUP_PERCENTAGE

        dyn_price, dyn_price_expl = calculate_dynamic_price(
            [p_item for p_item in self.search_results_data if p_item.get("id") != product.get("id")],
            markup_percentage=markup_percentage
        )
        demand_level, demand_expl = predict_demand_simple(product)

        semi_bold_weight = ft.FontWeight.W_600
        content_list = [
            ft.Row([
                ft.Container(
                    ft.Image(
                        src=product.get("image_url", "https://via.placeholder.com/80x80.png?text=No+Img"),
                        width=80, height=80, fit=ft.ImageFit.CONTAIN, border_radius=5,
                        error_content=ft.Icon(name=ft.Icons.BROKEN_IMAGE, color=APP_THEME_COLORS.get("text_secondary"))
                    ),
                    width=80, height=80,
                    bgcolor=APP_THEME_COLORS.get("surface_opacity_005"),
                    margin=ft.margin.only(right=15)
                ),
                ft.Column([
                    ft.Text(product.get("name", "N/A"), weight=ft.FontWeight.BOLD, size=17, color=APP_THEME_COLORS.get("on_surface")),
                    ft.Text(f"Маркетплейс: {product.get('marketplace', 'N/A')}", size=12, color=APP_THEME_COLORS.get("text_secondary")),
                    ft.Text(f"Цена: {product.get('price', 'N/A')} ₽", color=APP_THEME_COLORS.get("primary"), weight=ft.FontWeight.BOLD, size=15),
                ], expand=True, spacing=3, alignment=ft.MainAxisAlignment.CENTER)
            ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ft.Divider(height=1, color=APP_THEME_COLORS.get("border_color")),
            ft.Text("Описание:", weight=semi_bold_weight, color=APP_THEME_COLORS.get("on_surface")),
            ft.Text(product.get("description", "Нет описания"), max_lines=4, overflow=ft.TextOverflow.ELLIPSIS, tooltip=product.get("description", "Нет описания"), size=12, color=APP_THEME_COLORS.get("text_secondary")),
            ft.Row([
                ft.Text(f"Рейтинг: {product.get('rating', 'N/A')}/5", weight=semi_bold_weight),
                ft.Text(f"Отзывы: {product.get('reviews_count', 0)}")
            ], spacing=15, wrap=True),
            ft.Text(f"Доставка: {product.get('delivery_time', 'N/A')}", size=12, color=APP_THEME_COLORS.get("text_secondary")),
            ft.Divider(height=1, color=APP_THEME_COLORS.get("border_color")),
            ft.Text("Аналитика (AI):", weight=semi_bold_weight, color=APP_THEME_COLORS.get("primary")),
            ft.Text(f"Рекомендованная цена: {dyn_price if dyn_price is not None else 'Н/Д'} ₽", tooltip=dyn_price_expl, size=12),
            ft.Text(f"Прогноз спроса: {demand_level}", tooltip=demand_expl, size=12),
        ]

        product_page_url = product.get("product_url")
        url_target_val = "_blank"
        if hasattr(ft, 'UrlTarget') and hasattr(ft.UrlTarget, 'BLANK'):
            url_target_val = ft.UrlTarget.BLANK

        if product_page_url and isinstance(product_page_url, str) and not product_page_url.startswith("#mock"):
            content_list.append(
                ft.TextButton(
                    "Перейти на страницу товара",
                    icon=ft.Icons.OPEN_IN_NEW,
                    url=str(product_page_url),
                    style=ft.ButtonStyle(color=APP_THEME_COLORS.get("primary")),
                    url_target=url_target_val
                )
            )

        dialog_content = ft.Container(
            content=ft.Column([
                ft.Text("Детали товара", weight=ft.FontWeight.BOLD, color=APP_THEME_COLORS.get("primary")),
                ft.Column(content_list, spacing=8, scroll=ft.ScrollMode.ADAPTIVE, expand=True),
                ft.TextButton("Закрыть", on_click=self.close_overlay_event, style=ft.ButtonStyle(color=APP_THEME_COLORS.get("primary")))
            ], spacing=10),
            bgcolor=APP_THEME_COLORS.get("surface"),
            border_radius=10,
            padding=ft.padding.all(15),
            width=450,
            height=min(500, self.page.height - 120 if self.page.height else 500),
            shadow=ft.BoxShadow(blur_radius=10, color=APP_THEME_COLORS.get("black_with_opacity_85", "#000000D9"))
        )

        self.overlay_content.content.controls = [dialog_content]
        self.overlay_content.visible = True
        self.page.update()
        logger.info(f"Product details overlay opened for: {product.get('name')}")

    def toggle_compare_product_event(self, product_to_toggle: dict):
        logger.info(f"toggle_compare_product_event for: {product_to_toggle.get('name')}, current list size: {len(self.products_to_compare)}")
        key_to_find = (product_to_toggle.get('id'), product_to_toggle.get('marketplace'))
        found_idx = -1
        for i, p_comp_item in enumerate(self.products_to_compare):
            if (p_comp_item.get('id'), p_comp_item.get('marketplace')) == key_to_find:
                found_idx = i
                break

        if found_idx != -1:
            self.products_to_compare.pop(found_idx)
            logger.info(f"Removed from comparison: {product_to_toggle.get('name')}. New list size: {len(self.products_to_compare)}")
        else:
            if len(self.products_to_compare) < 5:
                self.products_to_compare.append(product_to_toggle)
                logger.info(f"Added to comparison: {product_to_toggle.get('name')}. New list size: {len(self.products_to_compare)}")
            else:
                self._show_snackbar("Можно сравнить не более 5 товаров.", APP_THEME_COLORS.get("error"))
                return

        self.update_compare_panel_display()
        self.refresh_all_product_cards_compare_status_display()
        self.update()

    def update_compare_panel_display(self):
        logger.info(f"Updating compare panel display, {len(self.products_to_compare)} items.")
        self.compare_list_view.controls.clear()
        if self.products_to_compare:
            for p_comp_item in self.products_to_compare:
                self.compare_list_view.controls.append(
                    ft.ListTile(
                        leading=ft.Container(ft.Image(src=p_comp_item.get("image_url"), width=30, height=30, fit=ft.ImageFit.CONTAIN, border_radius=5), padding=ft.padding.only(right=8)),
                        title=ft.Text(f"{p_comp_item.get('name', 'N/A')[:25]}...", size=12, color=APP_THEME_COLORS.get("on_surface")),
                        subtitle=ft.Text(f"{p_comp_item.get('marketplace')} - {p_comp_item.get('price')} ₽", size=10, color=APP_THEME_COLORS.get("text_secondary")),
                        trailing=ft.IconButton(
                            icon=ft.Icons.REMOVE_CIRCLE_OUTLINE,
                            icon_color=APP_THEME_COLORS.get("error"),
                            data=p_comp_item,
                            on_click=lambda _e, item=p_comp_item: self.toggle_compare_product_event(item),
                            icon_size=20, tooltip="Убрать"
                        ),
                        dense=True, content_padding=ft.padding.symmetric(horizontal=8, vertical=2)
                    )
                )
            self.compare_panel.visible = True
            self.compare_panel_action_button.visible = True
        else:
            self.compare_panel.visible = False
            self.compare_panel_action_button.visible = False
        self.compare_list_view.visible = bool(self.products_to_compare)

    def refresh_all_product_cards_compare_status_display(self):
        logger.info(f"Refreshing all product cards compare status. Compare list size: {len(self.products_to_compare)}")
        new_card_controls = []
        for product_item_data in self.search_results_data:
            is_currently_compared = any(
                pc.get('id') == product_item_data.get('id') and
                pc.get('marketplace') == product_item_data.get('marketplace')
                for pc in self.products_to_compare
            )
            card = create_product_card(
                product_item_data,
                on_details_click=lambda p_data=product_item_data: self.page.run_task(self.show_product_details_event, p_data),
                on_compare_click=self.toggle_compare_product_event,
                is_compared=is_currently_compared,
                theme_colors=APP_THEME_COLORS
            )
            new_card_controls.append(ft.Column([card], col={"xs": 12, "sm": 6, "md": 4, "lg": 3, "xl": 2.4}))
        self.results_column_cards.controls = new_card_controls
        logger.info(f"Refreshed {len(new_card_controls)} product cards in results.")

        current_query = self.query_field.value.strip() if self.query_field.value else ""
        self.recommendations_container.controls.clear()
        recommendations = get_recommendations(self.search_results_data, current_query, top_n=4)
        search_results_ids = {(p.get('id'), p.get('marketplace')) for p in self.search_results_data}
        filtered_recommendations = [
            rec_item for rec_item in recommendations
            if (rec_item.get('id'), rec_item.get('marketplace')) not in search_results_ids
        ]
        logger.info(f"Refreshing recommendations: {len(recommendations)} items, filtered to {len(filtered_recommendations)} unique items.")
        if filtered_recommendations:
            self.recommendations_container.controls.append(
                ft.Text("Рекомендуем также:", weight=ft.FontWeight.BOLD, size=16, color=APP_THEME_COLORS.get("primary"))
            )
            rec_items_list_controls = []
            for rec_item_data in filtered_recommendations:
                is_rec_item_compared = any(
                    pc.get('id') == rec_item_data.get('id') and
                    pc.get('marketplace') == rec_item_data.get('marketplace')
                    for pc in self.products_to_compare
                )
                rec_card_control = create_product_card(
                    rec_item_data,
                    on_details_click=lambda p_data=rec_item_data: self.page.run_task(self.show_product_details_event, p_data),
                    on_compare_click=self.toggle_compare_product_event,
                    is_compared=is_rec_item_compared,
                    theme_colors=APP_THEME_COLORS
                )
                rec_items_list_controls.append(ft.Column([rec_card_control], col={"xs": 12, "sm": 6, "md": 4, "lg": 3}))
            if rec_items_list_controls:
                self.recommendations_container.controls.append(
                    ft.ResponsiveRow(rec_items_list_controls, spacing=10, run_spacing=10, alignment=ft.MainAxisAlignment.START)
                )
                logger.info(f"Refreshed {len(rec_items_list_controls)} recommendation cards.")
            self.recommendations_container.visible = True
        else:
            self.recommendations_container.visible = False
            logger.info("No unique recommendations to refresh after filtering.")

    def show_comparison_dialog_event(self, _e: ft.ControlEvent | None = None):
        if not self.products_to_compare:
            self._show_snackbar("Пожалуйста, выберите товары для сравнения.", APP_THEME_COLORS.get("error"))
            return

        logger.info(f"Show comparison overlay for {len(self.products_to_compare)} products.")

        headers = [ft.DataColumn(ft.Text("Параметр", weight=ft.FontWeight.BOLD, color=APP_THEME_COLORS.get("primary")))]
        for p_header in self.products_to_compare:
            headers.append(ft.DataColumn(ft.Container(
                ft.Text(p_header.get('name', 'N/A')[:18] + "...", tooltip=p_header.get('name'), size=11, weight=ft.FontWeight.W_600, color=APP_THEME_COLORS.get("on_surface")),
                width=100, alignment=ft.alignment.center_left
            )))

        params_to_compare = {
            "Цена, ₽": "price", "Рейтинг": "rating", "Отзывов": "reviews_count",
            "Маркетплейс": "marketplace", "Доставка": "delivery_time"
        }
        rows_data = []
        for param_name_iter, product_key_iter in params_to_compare.items():
            cells_list = [ft.DataCell(ft.Text(param_name_iter, size=11, color=APP_THEME_COLORS.get("text_secondary")))]
            for p_cell_item in self.products_to_compare:
                value_item = p_cell_item.get(product_key_iter, "N/A")
                cell_text_widget = ft.Text(str(value_item), size=11, color=APP_THEME_COLORS.get("on_surface"))
                if product_key_iter == "price":
                    cell_text_widget.weight = ft.FontWeight.BOLD
                    cell_text_widget.color = APP_THEME_COLORS.get("primary")
                cells_list.append(ft.DataCell(cell_text_widget))
            rows_data.append(ft.DataRow(cells=cells_list))

        table_widget_width = max(400, 110 * len(self.products_to_compare) + 150)
        logger.info(f"Table widget width calculated: {table_widget_width}")
        table_widget = ft.DataTable(
            columns=headers, rows=rows_data, column_spacing=10,
            data_row_min_height=28, heading_row_height=32,
            border=ft.border.all(1, APP_THEME_COLORS.get("border_color")), border_radius=5,
            width=table_widget_width,
            horizontal_lines=ft.BorderSide(1, APP_THEME_COLORS.get("border_color")),
            vertical_lines=ft.BorderSide(1, APP_THEME_COLORS.get("border_color"))
        )

        page_width_val = self.page.width if self.page.width and self.page.width > 0 else 800
        dialog_content_width = min(page_width_val - 60, table_widget_width + 40, 900)
        logger.info(f"Overlay content width: {dialog_content_width}, page width: {page_width_val}")

        dialog_content = ft.Container(
            content=ft.Column([
                ft.Text("Сравнение товаров", weight=ft.FontWeight.BOLD, color=APP_THEME_COLORS.get("primary")),
                ft.Column([table_widget], scroll=ft.ScrollMode.ADAPTIVE, expand=True),
                ft.TextButton("Закрыть", on_click=self.close_overlay_event, style=ft.ButtonStyle(color=APP_THEME_COLORS.get("primary")))
            ], spacing=10),
            bgcolor=APP_THEME_COLORS.get("surface"),
            border_radius=10,
            padding=ft.padding.all(15),
            width=dialog_content_width,
            height=min(500, self.page.height - 120 if self.page.height else 500),
            shadow=ft.BoxShadow(blur_radius=10, color=APP_THEME_COLORS.get("black_with_opacity_85", "#000000D9"))
        )

        self.overlay_content.content.controls = [dialog_content]
        self.overlay_content.visible = True
        self.page.update()
        logger.info("Comparison overlay opened.")

    def _on_export_csv_submit(self, e: ft.ControlEvent | None = None):
        try:
            csv_data = export_products_to_csv(self.search_results_data)
            with open("export.csv", "wb") as f:
                f.write(csv_data)
            self._show_snackbar("Экспорт завершён!", APP_THEME_COLORS.get("success"))
        except Exception as ex:
            logger.error(f"Export error: {ex}")