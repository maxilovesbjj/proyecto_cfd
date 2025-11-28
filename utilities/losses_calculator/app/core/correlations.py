"""
Correlaciones para el factor de fricción Darcy-Weisbach.
Correlations for the Darcy-Weisbach friction factor.

Incluye:
- Flujo laminar: f = 64 / Re
- Flujo turbulento en tubería lisa: Blasius
- Flujo turbulento en tubería lisa o rugosa: Haaland
- Régimen transicional: interpolación entre laminar y turbulento.

Includes:
- Laminar flow: f = 64 / Re
- Turbulent flow in smooth pipe: Blasius
- Turbulent flow in smooth or rough pipe: Haaland
- Transitional regime: interpolation between laminar and turbulent.
"""

import math
from typing import Literal

# Allowed correlation methods for turbulent flow.
# Métodos de correlación permitidos para flujo turbulento.
CorrelationMethod = Literal["blasius", "haaland"]


def friction_factor_laminar(Re: float) -> float:
    """
    Coeficiente de fricción para flujo laminar:
    Laminar-flow friction factor:

        f = 64 / Re

    Parámetros / Parameters
    -----------------------
    Re : float
        Número de Reynolds / Reynolds number.

    Returns
    -------
    float
        Factor de fricción Darcy-Weisbach / Darcy-Weisbach friction factor.
    """
    if Re <= 0:
        raise ValueError(
            "Re must be > 0 to compute the friction factor "
            "(Re debe ser > 0 para calcular el factor de fricción)."
        )
    return 64.0 / Re


def friction_factor_blasius(Re: float) -> float:
    """
    Correlación de Blasius para flujo turbulento en tuberías lisas:
    Blasius correlation for turbulent flow in smooth pipes:

        f = 0.3164 * Re^(-0.25)

    Válida aproximadamente para / Valid approximately for:
        4e3 < Re < 1e5.
    """
    if Re <= 0:
        raise ValueError(
            "Re must be > 0 to compute the friction factor "
            "(Re debe ser > 0 para calcular el factor de fricción)."
        )
    return 0.3164 * (Re ** -0.25)


def friction_factor_haaland(Re: float, diameter_m: float, roughness_m: float) -> float:
    """
    Ecuación explícita de Haaland para flujo turbulento
    en tubería lisa o rugosa.

    Haaland explicit correlation for turbulent flow
    in smooth or rough pipes:

        1/sqrt(f) = -1.8 * log10( [ (ε/D)/3.7 ]^1.11 + 6.9/Re )

    donde / where:
      - ε es la rugosidad absoluta [m] / ε is the absolute roughness [m]
      - D el diámetro [m]           / D is the diameter [m]
    """
    if Re <= 0:
        raise ValueError(
            "Re must be > 0 to compute the friction factor "
            "(Re debe ser > 0 para calcular el factor de fricción)."
        )
    if diameter_m <= 0:
        raise ValueError(
            "Diameter must be > 0 "
            "(el diámetro debe ser > 0)."
        )
    if roughness_m < 0:
        raise ValueError(
            "Roughness cannot be negative "
            "(la rugosidad no puede ser negativa)."
        )

    eps_over_D = (roughness_m / diameter_m) if diameter_m > 0 else 0.0
    term = (eps_over_D / 3.7) ** 1.11 + 6.9 / Re
    if term <= 0:
        raise ValueError(
            "The Haaland log term must be positive "
            "(el término dentro del logaritmo de Haaland debe ser positivo)."
        )

    inv_sqrt_f = -1.8 * math.log10(term)
    f = 1.0 / (inv_sqrt_f ** 2)
    return f


def classify_regime(Re: float) -> str:
    """
    Clasificación del régimen de flujo según el número de Reynolds.
    Flow regime classification based on the Reynolds number.

    Convención devuelta / Returned convention:
      - 'laminar'
      - 'transicional'
      - 'turbulento'
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
    Cálculo del coeficiente de fricción Darcy-Weisbach (f).
    Computation of the Darcy-Weisbach friction factor (f).

    Lógica / Logic:
    ---------------
    - Re < 2000: flujo laminar / laminar flow  (64/Re)
    - Re > 4000: flujo turbulento / turbulent flow
        - Blasius: tubería lisa / smooth pipe
        - Haaland: tubería rugosa o lisa / rough or smooth pipe
    - 2000 <= Re <= 4000: región transicional / transitional region
        -> se interpola linealmente entre laminar y turbulento (en Re=4000).
           linearly interpolate between laminar and turbulent (at Re=4000).
    """
    if Re <= 0:
        raise ValueError(
            "Re must be > 0 to compute the friction factor "
            "(Re debe ser > 0 para calcular el factor de fricción)."
        )

    # Laminar region
    # Región laminar
    if Re < 2000.0:
        return friction_factor_laminar(Re)

    # Fully turbulent region
    # Región turbulenta "pura"
    if Re > 4000.0:
        if method == "blasius":
            return friction_factor_blasius(Re)
        elif method == "haaland":
            return friction_factor_haaland(Re, diameter_m, roughness_m)
        else:
            raise ValueError(
                f"Unknown correlation method: {method} "
                "(método de correlación no reconocido)."
            )

    # Transitional region: 2000 <= Re <= 4000
    # Región transicional: 2000 <= Re <= 4000
    # Interpolate between:
    #   - f_lam: laminar f at actual Re
    #   - f_turb_4000: turbulent f evaluated at Re = 4000
    f_lam = friction_factor_laminar(Re)

    if method == "blasius":
        f_turb_4000 = friction_factor_blasius(4000.0)
    else:
        f_turb_4000 = friction_factor_haaland(4000.0, diameter_m, roughness_m)

    w = (Re - 2000.0) / 2000.0  # goes from 0 to 1 between Re=2000 and Re=4000
    f_interp = (1.0 - w) * f_lam + w * f_turb_4000
    return f_interp
