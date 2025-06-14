import flet as ft
import logging
from config.settings import PRICE_MARKUP_PERCENTAGE
import numpy as np 
logger = logging.getLogger(__name__)

APP_THEME_COLORS = {
    "primary": "#1DB954",  # Зеленый цвет (как в Spotify)
    "secondary": "#535353",  # Темно-серый
    "surface": "#FFFFFF",  # Белый фон
    "background": "#F9F9F9",  # Светло-серый фон страницы
    "on_primary": "#FFFFFF",  # Текст на первичном цвете
    "on_surface": "#212121",  # Текст на поверхности
    "text_secondary": "#757575",  # Вторичный текст
    "border_color": "#E0E0E0",  # Цвет границ
    "error": "#CF6679",  # Цвет ошибок
    "success": "#4CAF50",  # Цвет успеха
    "surface_opacity_005": "#E0E0E0",  # Полупрозрачная поверхность
    "primary_opacity_01": "#1DB9541A",  # Полупрозрачный primary
    "black_with_opacity_85": "#000000D9",  # Черный с прозрачностью
}

def apply_theme(page):
    logger.info("Applying theme to page using ft.colors...")
    page.theme = ft.Theme(
        color_scheme=ft.ColorScheme(
            primary=ft.Colors.from_hex(APP_THEME_COLORS["primary"]),
            secondary=ft.Colors.from_hex(APP_THEME_COLORS["secondary"]),
            surface=ft.Colors.from_hex(APP_THEME_COLORS["surface"]),
            background=ft.Colors.from_hex(APP_THEME_COLORS["background"]),
            on_primary=ft.Colors.from_hex(APP_THEME_COLORS["on_primary"]),
            on_surface=ft.Colors.from_hex(APP_THEME_COLORS["on_surface"]),
            error=ft.Colors.from_hex(APP_THEME_COLORS["error"]),
            on_error=ft.Colors.from_hex(APP_THEME_COLORS["on_primary"]),
        )
    )
    logger.info("Theme applied successfully.")

def create_product_card(
    product: dict,
    on_details_click=None,
    on_compare_click=None,
    is_compared: bool = False,
    theme_colors: dict | None = None 
):
    ct = theme_colors or APP_THEME_COLORS
    
    primary_color = ct.get("primary")
    secondary_color = ct.get("secondary")
    on_surface_color = ct.get("on_surface")
    text_secondary_color = ct.get("text_secondary")
    card_bgcolor = ct.get("on_surface_opacity_008")
    border_color_card = ct.get("secondary_opacity_03")
    image_container_bgcolor = ct.get("surface_opacity_005")
    star_icon_color = ct.get("amber_accent_700")
    divider_transparent_color = ct.get("transparent")

    handle_details_click = on_details_click if callable(on_details_click) else lambda _p: logger.debug(f"Pcard details_click N/A: {product.get('name')}")
    handle_compare_click = on_compare_click if callable(on_compare_click) else lambda _p: logger.debug(f"Pcard compare_click N/A: {product.get('name')}")

    details_button = ft.TextButton(
        content=ft.Row([ft.Icon(name=ft.Icons.INFO_OUTLINE_ROUNDED, color=primary_color), ft.Text("Детали", color=primary_color)]),
        on_click=lambda _e: handle_details_click(product), height=35,
    )
    compare_icon_name = ft.Icons.COMPARE_ARROWS_ROUNDED if not is_compared else ft.Icons.CHECK_CIRCLE_ROUNDED
    compare_text = "Сравнить" if not is_compared else "Убрать"
    current_compare_color = primary_color if not is_compared else secondary_color
    compare_button = ft.TextButton(
        content=ft.Row([ft.Icon(name=compare_icon_name, color=current_compare_color), ft.Text(compare_text, color=current_compare_color)]),
        on_click=lambda _e: handle_compare_click(product), height=35,
    )
    image_container = ft.Container(
        content=ft.Image(src=product.get("image_url", "https://via.placeholder.com/200x200.png?text=No+Image"),fit=ft.ImageFit.CONTAIN,error_content=ft.Icon(name=ft.icons.BROKEN_IMAGE_OUTLINED, size=40, color=text_secondary_color)),
        width=float('inf'), height=160, bgcolor=image_container_bgcolor,
        border_radius=ft.BorderRadius(top_left=8, top_right=8, bottom_left=0, bottom_right=0),
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
    )
    card_content_column = ft.Column(
        [
            ft.Text(product.get("name", "N/A"),size=15, weight=ft.FontWeight.BOLD, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS,tooltip=product.get("name", "N/A"), color=on_surface_color),
            ft.Text(f"{product.get('description', 'N/A')[:70]}..." if product.get('description') else "N/A",size=11, color=text_secondary_color, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS,tooltip=product.get("description", "N/A")),
            ft.Row([ft.Text(f"{product.get('price', 'N/A')} ₽", size=14, weight=ft.FontWeight.BOLD, color=primary_color),ft.Text(f"({product.get('marketplace', 'N/A')})", size=10, color=text_secondary_color, italic=True)],alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Row([ft.Icon(name=ft.icons.STAR_ROUNDED, color=star_icon_color, size=16),ft.Text(f"{product.get('rating', '0.0')}/5 ({product.get('reviews_count', 0)})", size=11, color=text_secondary_color)],spacing=4, alignment=ft.MainAxisAlignment.START),
            ft.Text(f"Доставка: {product.get('delivery_time', 'N/A')}", size=11, color=text_secondary_color),
            ft.Divider(height=8, color=divider_transparent_color),
            ft.Row([details_button, compare_button],alignment=ft.MainAxisAlignment.SPACE_EVENLY)
        ], spacing=6,
    )
    return ft.Card(
        elevation=2,
        content=ft.Container(
            content=ft.Column([image_container, ft.Container(padding=ft.padding.all(12), content=card_content_column)], spacing=0),
            width=260, border_radius=ft.border_radius.all(8), bgcolor=card_bgcolor,
            border=ft.border.all(1, border_color_card),
        )
    )

def create_price_chart(products: list[dict], theme_colors: dict | None = None):
    ct = theme_colors or APP_THEME_COLORS
    on_surface_color = ct.get("on_surface")
    primary_color = ct.get("primary")
    secondary_color = ct.get("secondary")

    if not products: return ft.Text("Нет данных для графика.", color=on_surface_color)
    valid_products = [p for p in products if isinstance(p.get("price"), (int, float)) and p.get("price") > 0]
    if not valid_products: return ft.Text("Нет цен для графика.", color=on_surface_color)

    max_items_on_chart = 10
    products_on_chart = sorted(valid_products, key=lambda p: p.get("price", 0.0))[:max_items_on_chart]
    
    chart_palette_base = [
        primary_color, secondary_color, 
        ct.get("orange_accent_400"), 
        ct.get("lime_accent_700"),
        ct.get("purple_accent_200")
    ]
    chart_palette = [color for color in chart_palette_base if color is not None]
    if not chart_palette: chart_palette = [APP_THEME_COLORS["primary"]]

    tooltip_bgcolor_val = ct.get("black_with_opacity_85")
    grid_lines_color_val = ft.colors.with_opacity(0.15, on_surface_color) # Используем ft.colors напрямую
    chart_bg_color_val = ct.get("primary_opacity_01")
    
    bar_groups = []; bottom_axis_labels = []
    max_price_val = 0.0
    if products_on_chart:
        prices_on_chart = [float(p.get("price", 0.0)) for p in products_on_chart]
        if prices_on_chart: max_price_val = max(prices_on_chart)

    for i, product_item in enumerate(products_on_chart):
        price = float(product_item.get("price", 0.0))
        label_name = product_item.get("name", f"T{i+1}")[:10]+"..."
        tooltip_name = product_item.get("name", f"Товар {i+1}")
        bar_groups.append(ft.BarChartGroup(x=i,bar_rods=[ft.BarChartRod(from_y=0, to_y=price, width=20,color=chart_palette[i % len(chart_palette)],tooltip=f"{tooltip_name}\n{price:.2f} ₽",border_radius=2)]))
        bottom_axis_labels.append(ft.ChartAxisLabel(value=i, label=ft.Container(ft.Text(label_name, size=9, color=on_surface_color, tooltip=tooltip_name, text_align=ft.TextAlign.CENTER, width=50, no_wrap=False), width=50, alignment=ft.alignment.center)))
    
    if not bar_groups: return ft.Text("Нет данных для столбцов.", color=on_surface_color)
    
    y_step: float; y_num_intervals: int = 5
    if max_price_val == 0: y_step = 100.0
    elif max_price_val <= 1000: y_step = 100.0
    elif max_price_val <= 5000: y_step = 500.0
    elif max_price_val <= 10000: y_step = 1000.0
    elif max_price_val <= 50000: y_step = 5000.0
    else: y_step = 10000.0
    if max_price_val > 0 and y_step > 0: y_num_intervals = int(max_price_val / y_step) + 2
    y_num_intervals = max(y_num_intervals, 2)
    left_axis_labels = [ft.ChartAxisLabel(value=val * y_step, label=ft.Text(f"{int(val * y_step)}", size=9, color=on_surface_color)) for val in range(y_num_intervals)]
    chart_widget = ft.BarChart(bar_groups=bar_groups,bottom_axis=ft.ChartAxis(labels=bottom_axis_labels, labels_size=50),left_axis=ft.ChartAxis(labels=left_axis_labels, labels_size=35,title=ft.Text("Цена (₽)", color=on_surface_color, size=11, weight=ft.FontWeight.BOLD),title_size=20),horizontal_grid_lines=ft.ChartGridLines(interval=y_step, color=grid_lines_color_val, width=1),tooltip_bgcolor=tooltip_bgcolor_val,interactive=True,height=280,expand=True)
    return ft.Container(content=chart_widget, padding=ft.padding.all(10), border_radius=ft.border_radius.all(8),bgcolor=chart_bg_color_val,margin=ft.margin.only(bottom=10, top=5))

def calculate_dynamic_price(products: list[dict], own_product_name: str | None = None, markup_percentage: float = PRICE_MARKUP_PERCENTAGE) -> tuple[float | None, str]:
    competitor_prices = []
    for p_item in products:
        if own_product_name and p_item.get("name") == own_product_name: continue
        price_val = p_item.get("price")
        if isinstance(price_val, (int, float)) and price_val > 0: competitor_prices.append(price_val)
    if not competitor_prices: return None, "Нет данных о ценах конкурентов."
    avg_competitor_price = sum(competitor_prices) / len(competitor_prices)
    min_price_val = min(competitor_prices); max_price_val = max(competitor_prices)
    recommended_price = avg_competitor_price * (1 + markup_percentage / 100.0)
    explanation = (f"Анализ ({len(competitor_prices)} конкурентов):\n"
                   f"- Цены: {min_price_val:.2f} - {max_price_val:.2f} ₽\n"
                   f"- Средняя: {avg_competitor_price:.2f} ₽\n"
                   f"Рекомендация (+{markup_percentage:.0f}%): {recommended_price:.2f} ₽")
    return round(recommended_price, 2), explanation

def predict_demand_simple(product: dict) -> tuple[str, str]:
    rating_val = float(product.get("rating", 0.0)); reviews_val = int(product.get("reviews_count", 0))
    score = 0
    if rating_val >= 4.5: score += 3
    elif rating_val >= 4.0: score += 2
    elif rating_val >= 3.0: score += 1
    if reviews_val >= 1000: score += 3
    elif reviews_val >= 100: score += 2
    elif reviews_val >= 10: score += 1
    demand_level = "Низкий"; explanation_suffix = " (новый/нишевый?)"
    if score >= 5: demand_level = "Высокий"; explanation_suffix = " (популярный)"
    elif score >= 3: demand_level = "Средний"; explanation_suffix = " (стабильный интерес)"
    explanation = (f"Анализ спроса:\n"
                   f"- Рейтинг: {rating_val:.1f}/5, Отзывы: {reviews_val}\n"
                   f"- Привлекательность: {score}/6\n"
                   f"Прогноз: {demand_level}{explanation_suffix}")
    return demand_level, explanation

