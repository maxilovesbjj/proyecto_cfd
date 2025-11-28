"""
Servicios para el cálculo de pérdidas de carga por fricción en tuberías.
Services for computing head losses due to friction in pipe flows.

Incluye funciones para:
- Área de sección circular
- Velocidad media
- Número de Reynolds
- Pérdida de carga en un tramo
- Pérdida de carga total en varios tramos en serie

Includes functions for:
- Circular cross-section area
- Mean velocity
- Reynolds number
- Head loss in a single segment
- Total head loss in several segments in series
"""

import math
from typing import Dict, List

from app.core.correlations import friction_factor, classify_regime, CorrelationMethod
from app.geometry.pipe_geometries import PipeSegment


def compute_area(diameter_m: float) -> float:
    """
    Área de la sección transversal de una tubería circular [m²].
    Cross-sectional area of a circular pipe [m²].

    Parameters
    ----------
    diameter_m : float
        Diámetro interno de la tubería [m].
        Internal pipe diameter [m].

    Returns
    -------
    float
        Área de la sección [m²] / Cross-sectional area [m²].
    """
    return math.pi * (diameter_m ** 2) / 4.0


def compute_velocity(q_m3s: float, area_m2: float) -> float:
    """
    Velocidad media del fluido [m/s].
    Mean fluid velocity [m/s].

    Parameters
    ----------
    q_m3s : float
        Caudal volumétrico [m³/s].
        Volumetric flow rate [m³/s].
    area_m2 : float
        Área de sección transversal [m²].
        Cross-sectional area [m²].

    Returns
    -------
    float
        Velocidad media [m/s] / Mean velocity [m/s].
    """
    if area_m2 <= 0:
        raise ValueError(
            "Area must be > 0 (el área debe ser > 0)."
        )
    return q_m3s / area_m2


def compute_reynolds(velocity_ms: float, diameter_m: float, rho: float, mu: float) -> float:
    """
    Número de Reynolds:
    Reynolds number:

        Re = (rho * v * D) / mu

    Parameters
    ----------
    velocity_ms : float
        Velocidad media [m/s] / Mean velocity [m/s].
    diameter_m : float
        Diámetro interno [m] / Internal diameter [m].
    rho : float
        Densidad del fluido [kg/m³] / Fluid density [kg/m³].
    mu : float
        Viscosidad dinámica [Pa·s] / Dynamic viscosity [Pa·s].

    Returns
    -------
    float
        Número de Reynolds / Reynolds number.
    """
    if mu <= 0 or rho <= 0:
        raise ValueError(
            "rho and mu must be > 0 (rho y mu deben ser > 0)."
        )
    if diameter_m <= 0:
        raise ValueError(
            "Diameter must be > 0 (el diámetro debe ser > 0)."
        )
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
    Compute friction head loss in a single pipe segment.

    Parameters
    ----------
    q_m3s : float
        Caudal volumétrico [m³/s] / Volumetric flow rate [m³/s].
    segment : PipeSegment
        Tramo de tubería / Pipe segment definition.
    rho : float
        Densidad [kg/m³] / Density [kg/m³].
    mu : float
        Viscosidad dinámica [Pa·s] / Dynamic viscosity [Pa·s].
    g : float
        Aceleración de la gravedad [m/s²] / Gravity acceleration [m/s²].
    method : CorrelationMethod, optional
        Método de correlación para f ("blasius" o "haaland").
        Correlation method for f ("blasius" or "haaland").

    Returns
    -------
    Dict[str, float]
        Diccionario con magnitudes calculadas:
        Dictionary with computed quantities:

          - area_m2        : área interna [m²] / internal area [m²]
          - velocity_ms    : velocidad media [m/s] / mean velocity [m/s]
          - reynolds       : número de Reynolds / Reynolds number
          - regime         : régimen de flujo (código texto) / flow regime (string code)
          - friction_factor: factor f de Darcy-Weisbach / Darcy-Weisbach f
          - hf_m           : pérdida de carga [m] / head loss [m]
          - delta_p_pa     : pérdida de presión [Pa] / pressure drop [Pa]
          - delta_p_bar    : pérdida de presión [bar] / pressure drop [bar]
    """
    if q_m3s <= 0:
        raise ValueError(
            "Flow rate must be > 0 (el caudal debe ser > 0)."
        )
    if rho <= 0 or mu <= 0:
        raise ValueError(
            "rho and mu must be > 0 (rho y mu deben ser > 0)."
        )
    if g <= 0:
        raise ValueError(
            "g must be > 0 (g debe ser > 0)."
        )

    L = segment.length_m
    D = segment.diameter_m
    eps = segment.roughness_m

    area_m2 = compute_area(D)
    velocity_ms = compute_velocity(q_m3s, area_m2)
    reynolds = compute_reynolds(velocity_ms, D, rho, mu)
    f = friction_factor(reynolds, D, eps, method=method)
    regime = classify_regime(reynolds)

    head_velocity = (velocity_ms ** 2) / (2.0 * g)
    hf_m = f * (L / D) * head_velocity  # pérdida de carga [m] / head loss [m]

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

    Compute total head loss in several pipe segments in series
    (same flow rate for all segments).

    Parameters
    ----------
    q_m3s : float
        Caudal volumétrico [m³/s] / Volumetric flow rate [m³/s].
    segments : List[PipeSegment]
        Lista de tramos en serie / List of pipe segments in series.
    rho : float
        Densidad [kg/m³] / Density [kg/m³].
    mu : float
        Viscosidad dinámica [Pa·s] / Dynamic viscosity [Pa·s].
    g : float
        Aceleración de la gravedad [m/s²] / Gravity acceleration [m/s²].
    method : CorrelationMethod, optional
        Método de correlación para f / Correlation method for f.

    Returns
    -------
    Dict[str, object]
        Estructura con:
        Structure with:

          - segments_results : lista de resultados por tramo
                               list of per-segment results (dicts)
          - hf_total_m       : pérdida de carga total [m]
                               total head loss [m]
          - delta_p_total_pa : caída de presión total [Pa]
                               total pressure drop [Pa]
          - delta_p_total_bar: caída de presión total [bar]
                               total pressure drop [bar]
    """
    if not segments:
        raise ValueError(
            "At least one pipe segment must be provided "
            "(debe proporcionar al menos un tramo de tubería)."
        )

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

        seg_info: Dict[str, object] = {
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
