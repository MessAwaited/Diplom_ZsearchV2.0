from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import logging

logger = logging.getLogger(__name__)

def get_product_text_representation(product: dict) -> str:
    name = product.get("name", "")
    description = product.get("description", "")
    return f"{name} {description}".lower()

def get_recommendations(products: list[dict], query: str, top_n: int = 3) -> list[dict]:
    if not products:
        return []
    if not query:
        return sorted(
            products, 
            key=lambda p: (float(p.get("rating", 0.0)), -float(p.get("price", float('inf')))), 
            reverse=True
        )[:top_n]

    try:
        product_texts = [get_product_text_representation(p) for p in products]
        all_texts = product_texts + [query.lower()]
        vectorizer = TfidfVectorizer(stop_words=None)
        tfidf_matrix = vectorizer.fit_transform(all_texts)
        query_vector = tfidf_matrix[-1]
        product_vectors = tfidf_matrix[:-1]

        if product_vectors.shape[0] == 0:
            return []

        cosine_similarities = cosine_similarity(query_vector, product_vectors).flatten()

        for i, product_item in enumerate(products):
            relevance_score = cosine_similarities[i]
            price = float(str(product_item.get("price", "0")).replace(",", "."))
            price_score = 0.0
            if price > 0:
                price_score = 1.0 / (1.0 + np.log1p(price))
            rating = float(product_item.get("rating", 0.0))
            rating_score = rating / 5.0 if 0.0 <= rating <= 5.0 else (1.0 if rating > 5.0 else 0.0)
            
            w_relevance = 0.6
            w_rating = 0.3
            w_price = 0.1
            product_item["score"] = (w_relevance * relevance_score +
                                     w_rating * rating_score +
                                     w_price * price_score)
            product_item["debug_scores"] = {
                "relevance": relevance_score, "price_raw": price,
                "price_score_normalized": price_score, "rating_raw": rating,
                "rating_score_normalized": rating_score
            }
        recommended_products = sorted(products, key=lambda p: p.get("score", 0.0), reverse=True)
        logger.info(f"Generated {len(recommended_products[:top_n])} recommendations for '{query}'.")
        return recommended_products[:top_n]
    except Exception as e_rec:
        logger.error(f"Error in get_recommendations for '{query}': {e_rec}", exc_info=True)
        return sorted(products, key=lambda p: float(p.get("rating", 0.0)), reverse=True)[:top_n]