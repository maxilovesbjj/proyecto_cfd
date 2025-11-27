import math
from typing import Dict, List

from app.core.correlations import friction_factor, classify_regime, CorrelationMethod
from app.geometry.pipe_geometries import PipeSegment


def compute_area(diameter_m: float) -> float:
    """
    Área de la sección transversal de una tubería circular [m²].
    """
    return math.pi * (diameter_m ** 2) / 4.0


def compute_velocity(q_m3s: float, area_m2: float) -> float:
    """
    Velocidad media del fluido [m/s].
    """
    if area_m2 <= 0:
        raise ValueError("El área debe ser > 0.")
    return q_m3s / area_m2


def compute_reynolds(velocity_ms: float, diameter_m: float, rho: float, mu: float) -> float:
    """
    Número de Reynolds:
        Re = (rho * v * D) / mu
    """
    if mu <= 0 or rho <= 0:
        raise ValueError("rho y mu deben ser > 0.")
    if diameter_m <= 0:
        raise ValueError("El diámetro debe ser > 0.")
    return (rho * velocity_ms * diameter_m) / mu


def compute_single_segment_head_loss(
    q_m3s: float,
    segment: PipeSegment,
    rho: float,
    mu: float,
    g: float,
    method: CorrelationMethod = "haaland",
) -> Dict[str, float]:
    """
    Calcula la pérdida de carga por fricción en un único tramo de tubería.

    Retorna un diccionario con:
      - area_m2
      - velocity_ms
      - reynolds
      - regime
      - friction_factor
      - hf_m        (pérdida de carga en metros)
      - delta_p_pa  (pérdida de presión en Pa)
      - delta_p_bar (pérdida de presión en bar)
    """
    if q_m3s <= 0:
        raise ValueError("El caudal debe ser > 0.")
    if rho <= 0 or mu <= 0:
        raise ValueError("rho y mu deben ser > 0.")
    if g <= 0:
        raise ValueError("g debe ser > 0.")

    L = segment.length_m
    D = segment.diameter_m
    eps = segment.roughness_m

    area_m2 = compute_area(D)
    velocity_ms = compute_velocity(q_m3s, area_m2)
    reynolds = compute_reynolds(velocity_ms, D, rho, mu)
    f = friction_factor(reynolds, D, eps, method=method)
    regime = classify_regime(reynolds)

    head_velocity = (velocity_ms ** 2) / (2.0 * g)
    hf_m = f * (L / D) * head_velocity  # pérdida de carga [m]

    delta_p_pa = rho * g * hf_m
    delta_p_bar = delta_p_pa / 1.0e5

    return {
        "area_m2": area_m2,
        "velocity_ms": velocity_ms,
        "reynolds": reynolds,
        "regime": regime,
        "friction_factor": f,
        "hf_m": hf_m,
        "delta_p_pa": delta_p_pa,
        "delta_p_bar": delta_p_bar,
    }


def compute_series_head_loss(
    q_m3s: float,
    segments: List[PipeSegment],
    rho: float,
    mu: float,
    g: float,
    method: CorrelationMethod = "haaland",
) -> Dict[str, object]:
    """
    Calcula la pérdida de carga total en varios tramos de tubería en serie
    (mismo caudal para todos los tramos).

    Retorna:
      - segments_results: lista con resultados por tramo
      - hf_total_m
      - delta_p_total_pa
      - delta_p_total_bar
    """
    if not segments:
        raise ValueError("Debe proporcionar al menos un tramo de tubería.")

    total_hf = 0.0
    total_dp_pa = 0.0
    segments_results: List[Dict[str, object]] = []

    for seg in segments:
        res = compute_single_segment_head_loss(
            q_m3s=q_m3s,
            segment=seg,
            rho=rho,
            mu=mu,
            g=g,
            method=method,
        )
        total_hf += res["hf_m"]
        total_dp_pa += res["delta_p_pa"]

        seg_info = {
            "name": seg.name or "",
            "length_m": seg.length_m,
            "diameter_m": seg.diameter_m,
            "roughness_m": seg.roughness_m,
            **res,
        }
        segments_results.append(seg_info)

    delta_p_total_bar = total_dp_pa / 1.0e5

    return {
        "segments_results": segments_results,
        "hf_total_m": total_hf,
        "delta_p_total_pa": total_dp_pa,
        "delta_p_total_bar": delta_p_total_bar,
    }
