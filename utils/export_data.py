import csv
import io
import logging

logger = logging.getLogger(__name__)

def export_products_to_csv(products: list[dict]) -> bytes:
    if not products:
        logger.warning("No products provided to export_products_to_csv function.")
        return b""

    output_stream = io.StringIO(newline='')
    
    fieldnames = [
        "name", "marketplace", "price", "rating", "reviews_count",
        "delivery_time", "description", "product_url", "image_url"
    ]
    
    csv_writer = csv.DictWriter(output_stream, fieldnames=fieldnames, extrasaction='ignore', quoting=csv.QUOTE_NONNUMERIC)
    
    csv_writer.writeheader()
    
    for product_item in products:
        row_to_write = {
            key: (str(value).replace('\n', ' ').replace('\r', '') if value is not None else "") 
            for key, value in product_item.items()
        }
        csv_writer.writerow(row_to_write)
    
    csv_data_string = output_stream.getvalue()
    output_stream.close()
    
    logger.info(f"Successfully prepared CSV data for {len(products)} products.")
    return csv_data_string.encode('utf-8-sig')