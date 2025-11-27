"""
Coeficientes K para codos, según la tabla de referencia:

Codo 90° SR (≈1D)   -> K = 0.75
Codo 90° LR (≈1,5D) -> K = 0.45
Codo 45° SR (≈1D)   -> K = 0.35
Codo 45° LR (≈1,5D) -> K = 0.20
"""

from typing import Dict

ELBOWS: Dict[str, dict] = {
    "elbow_90_SR": {
        "K": 0.75,
        "label": "Codo 90° SR (≈1D, estándar)",
    },
    "elbow_90_LR": {
        "K": 0.25,
        "label": "Codo 90° LR (≈1,5D, radio largo)",
    },
    "elbow_45_SR": {
        "K": 0.35,
        "label": "Codo 45° SR (≈1D, estándar)",
    },
    "elbow_45_LR": {
        "K": 0.20,
        "label": "Codo 45° LR (≈1,5D, radio largo)",
    },
}


def get_elbow_k(code: str) -> float:
    """
    Devuelve el coeficiente K asociado a un codo.
    code:
      - "elbow_90_SR"
      - "elbow_90_LR"
      - "elbow_45_SR"
      - "elbow_45_LR"
    """
    try:
        return ELBOWS[code]["K"]
    except KeyError as exc:
        raise ValueError(f"Tipo de codo desconocido: {code}") from exc


def get_elbow_label(code: str) -> str:
    """
    Devuelve una descripción legible del codo.
    """
    try:
        return ELBOWS[code]["label"]
    except KeyError as exc:
        raise ValueError(f"Tipo de codo desconocido: {code}") from exc
