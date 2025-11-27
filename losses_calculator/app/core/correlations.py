import math
from typing import Literal

CorrelationMethod = Literal["blasius", "haaland"]


def friction_factor_laminar(Re: float) -> float:
    """
    Coeficiente de fricción para flujo laminar:
        f = 64 / Re
    """
    if Re <= 0:
        raise ValueError("Re debe ser > 0 para calcular el factor de fricción.")
    return 64.0 / Re


def friction_factor_blasius(Re: float) -> float:
    """
    Correlación de Blasius para flujo turbulento en tuberías lisas:
        f = 0.3164 * Re^(-0.25)
    Válida aproximadamente para 4e3 < Re < 1e5.
    """
    if Re <= 0:
        raise ValueError("Re debe ser > 0 para calcular el factor de fricción.")
    return 0.3164 * (Re ** -0.25)


def friction_factor_haaland(Re: float, diameter_m: float, roughness_m: float) -> float:
    """
    Ecuación explícita de Haaland para flujo turbulento (tubería rugosa o lisa):

        1/sqrt(f) = -1.8 * log10( [ (ε/D)/3.7 ]^1.11 + 6.9/Re )

    donde:
      - ε es la rugosidad absoluta [m]
      - D el diámetro [m]
    """
    if Re <= 0:
        raise ValueError("Re debe ser > 0 para calcular el factor de fricción.")
    if diameter_m <= 0:
        raise ValueError("El diámetro debe ser > 0.")
    if roughness_m < 0:
        raise ValueError("La rugosidad no puede ser negativa.")

    # Asegurar no división por cero
    eps_over_D = (roughness_m / diameter_m) if diameter_m > 0 else 0.0
    term = (eps_over_D / 3.7) ** 1.11 + 6.9 / Re
    if term <= 0:
        raise ValueError("El término dentro del logaritmo de Haaland debe ser positivo.")

    inv_sqrt_f = -1.8 * math.log10(term)
    f = 1.0 / (inv_sqrt_f ** 2)
    return f


def classify_regime(Re: float) -> str:
    """
    Clasificación del régimen de flujo según el número de Reynolds.
    """
    if Re < 2000:
        return "laminar"
    elif Re <= 4000:
        return "transicional"
    else:
        return "turbulento"


def friction_factor(
    Re: float,
    diameter_m: float,
    roughness_m: float,
    method: CorrelationMethod = "haaland",
) -> float:
    """
    Cálculo del coeficiente de fricción Darcy-Weisbach (f):

    - Re < 2000: flujo laminar (64/Re)
    - Re > 4000: flujo turbulento
        - Blasius: tubería lisa
        - Haaland: tubería rugosa/lisa
    - 2000 <= Re <= 4000: región transicional
        se interpola linealmente entre laminar y turbulento (en Re=4000).
    """
    if Re <= 0:
        raise ValueError("Re debe ser > 0 para calcular el factor de fricción.")

    # Laminar
    if Re < 2000.0:
        return friction_factor_laminar(Re)

    # Turbulento "puro"
    if Re > 4000.0:
        if method == "blasius":
            return friction_factor_blasius(Re)
        elif method == "haaland":
            return friction_factor_haaland(Re, diameter_m, roughness_m)
        else:
            raise ValueError(f"Método de correlación no reconocido: {method}")

    # Región transicional: 2000 <= Re <= 4000
    # Interpolamos entre:
    # - f_lam (laminar) evaluado en Re actual
    # - f_turb_4000 (turbulento) evaluado en Re=4000
    f_lam = friction_factor_laminar(Re)

    if method == "blasius":
        f_turb_4000 = friction_factor_blasius(4000.0)
    else:
        f_turb_4000 = friction_factor_haaland(4000.0, diameter_m, roughness_m)

    w = (Re - 2000.0) / 2000.0  # va de 0 a 1 entre Re=2000 y Re=4000
    f_interp = (1.0 - w) * f_lam + w * f_turb_4000
    return f_interp
