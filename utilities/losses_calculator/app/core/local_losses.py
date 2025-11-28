"""
Coeficientes K para pérdidas locales en codos.
Local loss K-coefficients for pipe elbows.

Basado en una tabla de referencia para codos estándar:
Based on a reference table for standard elbows:

  - Codo 90° SR (≈1D)   -> K = 0.75
  - Codo 90° LR (≈1,5D) -> K = 0.25
  - Codo 45° SR (≈1D)   -> K = 0.35
  - Codo 45° LR (≈1,5D) -> K = 0.20
"""

from typing import Dict


# Dictionary of elbow configurations and their K values.
# Diccionario de configuraciones de codos y sus coeficientes K.
ELBOWS: Dict[str, dict] = {
    "elbow_90_SR": {
        "K": 0.75,
        "label": "Codo 90° SR (≈1D, estándar) / 90° SR elbow (≈1D, standard)",
    },
    "elbow_90_LR": {
        "K": 0.25,
        "label": "Codo 90° LR (≈1,5D, radio largo) / 90° LR elbow (≈1.5D, long radius)",
    },
    "elbow_45_SR": {
        "K": 0.35,
        "label": "Codo 45° SR (≈1D, estándar) / 45° SR elbow (≈1D, standard)",
    },
    "elbow_45_LR": {
        "K": 0.20,
        "label": "Codo 45° LR (≈1,5D, radio largo) / 45° LR elbow (≈1.5D, long radius)",
    },
}


def get_elbow_k(code: str) -> float:
    """
    Devuelve el coeficiente K asociado a un codo.
    Returns the K coefficient associated with a given elbow.

    Parámetros / Parameters
    -----------------------
    code : str
        Código del codo, por ejemplo:
        Elbow code, for example:
          - "elbow_90_SR"
          - "elbow_90_LR"
          - "elbow_45_SR"
          - "elbow_45_LR"
    """
    try:
        return ELBOWS[code]["K"]
    except KeyError as exc:
        raise ValueError(
            f"Unknown elbow type: {code} "
            f"(tipo de codo desconocido: {code})"
        ) from exc


def get_elbow_label(code: str) -> str:
    """
    Devuelve una descripción legible del codo (ES/EN en una sola cadena).
    Returns a human-readable description of the elbow (ES/EN in a single string).
    """
    try:
        return ELBOWS[code]["label"]
    except KeyError as exc:
        raise ValueError(
            f"Unknown elbow type: {code} "
            f"(tipo de codo desconocido: {code})"
        ) from exc
