"""Limite de geometria visual; estatísticas sempre usam a consulta completa."""


def sample_rows(rows, limit):
    limit = max(2, int(limit))
    if len(rows) <= limit:
        return rows
    # Inclui ambos os extremos e nunca supera o limite configurado.
    return [rows[i * (len(rows) - 1) // (limit - 1)] for i in range(limit)]
