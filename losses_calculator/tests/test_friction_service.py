from app.core.constants import RHO_WATER_20C, MU_WATER_20C, G_DEFAULT, EPSILON_HDPE_DEFAULT
from app.geometry.pipe_geometries import PipeSegment
from app.services.friction_service import compute_single_segment_head_loss


def test_single_segment_basic():
    seg = PipeSegment(
        length_m=10.0,
        diameter_m=0.05,
        roughness_m=EPSILON_HDPE_DEFAULT,
        name="Tramo test",
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
