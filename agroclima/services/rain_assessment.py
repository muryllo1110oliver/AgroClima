"""Probabilidade horária e acumulado de 24 h têm classificações independentes."""


def classify_probability(probability):
    if probability is None:
        return "Indisponível", "Probabilidade indisponível", "neutral"
    if not 0 <= probability <= 100:
        raise ValueError("Probabilidade deve estar entre 0 e 100")
    for upper, classification, text, tone in (
        (20, "Muito baixa", "Chuva muito pouco provável", "neutral"),
        (40, "Baixa", "Chuva pouco provável", "prob_low"),
        (60, "Moderada", "Chuva com probabilidade moderada", "prob_moderate"),
        (80, "Alta", "Chuva provável", "prob_high"),
        (100, "Muito alta", "Chuva muito provável", "prob_very_high"),
    ):
        if probability <= upper:
            return classification, text, tone
    raise ValueError("Probabilidade deve estar entre 0 e 100")


def classify_volume(amount):
    # Limites compartilhados: 5 = baixo, 15 = moderado, 30 = elevado.
    if amount < 1:
        return "Insignificante", "neutral"
    if amount <= 5:
        return "Baixo", "volume_low"
    if amount <= 15:
        return "Moderado", "volume_moderate"
    if amount <= 30:
        return "Elevado", "volume_high"
    return "Muito elevado", "volume_very_high"


def irrigation_recommendation(soil, cfg, forecast):
    if soil >= cfg.soil_min_pct:
        return "Manter monitoramento. Umidade do solo dentro da faixa configurada."
    if forecast is None or forecast.precipitation_probability_max is None:
        return "Solo seco. Verificar a previsão meteorológica e a necessidade de irrigação da cultura."
    amount = forecast.precipitation_24h_mm
    probability = forecast.precipitation_probability_max
    relevant_volume = amount > 5 or (amount >= 1 and amount >= cfg.rain_block_mm)
    if probability > 60 and relevant_volume:
        return "Acompanhar a precipitação antes de irrigar."
    if probability > 60:
        return "Irrigação recomendada conforme a necessidade da cultura; a chuva provável tem volume baixo ou insignificante."
    if probability <= 40:
        return "Irrigação recomendada. Acompanhar a previsão, pois a probabilidade de chuva é baixa ou muito baixa."
    return "Avaliar irrigação conforme a necessidade da cultura e acompanhar a precipitação; a probabilidade de chuva é moderada."
