"""
Tests for the friction_service module.

Pruebas para el módulo friction_service.
Verifica que el cálculo de pérdidas de carga en un solo tramo
devuelva valores físicos razonables.
"""

from app.core.constants import (
    RHO_WATER_20C,
    MU_WATER_20C,
    G_DEFAULT,
    EPSILON_HDPE_DEFAULT,
)
from app.geometry.pipe_geometries import PipeSegment
from app.services.friction_service import compute_single_segment_head_loss


def test_single_segment_basic() -> None:
    """
    Basic sanity check for a single HDPE pipe segment with water at 20 °C.
    Prueba básica de coherencia para un tramo de tubería HDPE con agua a 20 °C.
    """
    seg = PipeSegment(
        length_m=10.0,
        diameter_m=0.05,
        roughness_m=EPSILON_HDPE_DEFAULT,
        name="Test segment / Tramo test",
    )

    res = compute_single_segment_head_loss(
        q_m3s=0.001,  # 1 L/s
        segment=seg,
        rho=RHO_WATER_20C,
        mu=MU_WATER_20C,
        g=G_DEFAULT,
        method="haaland",
    )

    assert res["hf_m"] > 0.0
    assert res["velocity_ms"] > 0.0
    assert res["reynolds"] > 0.0
