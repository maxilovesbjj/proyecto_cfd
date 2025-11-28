import math
from dataclasses import dataclass, asdict
from typing import List, Dict, Any

from .config import (
    get_level_config,
    get_algorithm_config,
    LevelConfig,
    AlgorithmConfig,
)


@dataclass
class GeometryInput:
    """
    Datos de entrada geométricos y de nivel de malla.
    Geometric input data and mesh level.
    """
    D: float          # diámetro interno [m] / internal diameter [m]
    L_in: float       # largo recto de entrada [m] / inlet straight length [m]
    L_out: float      # largo recto de salida [m] / outlet straight length [m]
    R: float          # radio del codo [m] / elbow radius [m]
    theta_deg: float  # ángulo del codo [°] / elbow angle [°]
    level: str        # coarse / medium / fine


@dataclass
class Netgen3DParams:
    """Parámetros globales NETGEN 3D / Global NETGEN 3D parameters."""
    max_size: float
    min_size: float
    growth_rate: float


@dataclass
class LocalSizeParams:
    """
    Tamaños locales sugeridos para hipótesis 'Local Sizes' en Salome.
    Suggested local mesh sizes for 'Local Sizes' hypothesis in Salome.
    """
    s_bulk: float
    s_elbow: float
    s_theta: float
    s_wall_elbow: float
    s_wall_straight: float


@dataclass
class OneDParams:
    """
    Números de segmentos 1D para entrada, salida y arco del codo.
    1D segment counts for inlet, outlet and elbow arc.
    """
    N_in: int
    N_out: int
    N_arc: int
    N_in_raw: int
    N_out_raw: int
    N_arc_raw: int


@dataclass
class ViscousLayerParams:
    """
    Parámetros para hipótesis 'Viscous Layers' en NETGEN 3D.
    Parameters for 'Viscous Layers' hypothesis in NETGEN 3D.
    """
    total_thickness: float
    number_of_layers: int
    stretch_factor: float


@dataclass
class NetgenArgumentsParams:
    """
    Parámetros específicos de la pestaña 'Arguments' de NETGEN 1D-2D-3D
    (o NETGEN 3D), más la recomendación de algoritmos.

    Specific parameters for the 'Arguments' tab of NETGEN 1D-2D-3D (or NETGEN 3D),
    plus recommended algorithms.
    """
    fineness: str
    nb_segs_per_edge: int
    nb_segs_per_radius: int
    chordal_error: float
    limit_size_by_curvature: bool
    quad_dominated: bool
    second_order: bool
    optimize: bool
    main_3d_algorithm: str
    alternative_3d_algorithm: str
    alternative_2d_algorithm: str
    alternative_1d_algorithm: str


@dataclass
class MeshRecommendations:
    """
    Estructura de salida principal con todas las recomendaciones de mallado.
    Main output structure with all mesh recommendations.
    """
    level: str
    geometry: GeometryInput
    netgen_3d: Netgen3DParams
    local_sizes: LocalSizeParams
    segments_1d: OneDParams
    viscous_layers: ViscousLayerParams
    netgen_arguments: NetgenArgumentsParams
    notes: List[str]

    def to_dict(self) -> Dict[str, Any]:
        """Convert everything to a dict (useful for JSON)."""
        return asdict(self)


def _validate_geometry(g: GeometryInput) -> None:
    """Basic geometry validation."""
    if g.D <= 0:
        raise ValueError("Diameter D must be > 0.")
    if g.R <= 0:
        raise ValueError("Elbow radius R must be > 0.")
    if g.theta_deg <= 0:
        raise ValueError("Elbow angle theta must be > 0.")
    if g.L_in < 0 or g.L_out < 0:
        raise ValueError("L_in and L_out cannot be negative.")


def compute_mesh_recommendations(geom: GeometryInput) -> MeshRecommendations:
    """
    Compute recommended mesh parameters for Salome/NETGEN
    from geometry and mesh level.
    """
    _validate_geometry(geom)

    cfg: LevelConfig = get_level_config(geom.level)
    algo_cfg: AlgorithmConfig = get_algorithm_config()
    notes: List[str] = []

    # R/D ratio (tighter elbows need more resolution)
    r_over_d = geom.R / geom.D

    # --- Base sizes ---
    N_bulk = cfg.N_bulk
    N_elbow = 2 * N_bulk            # rule: elbow ≈ 2 x axial bulk resolution
    s_bulk = geom.D / N_bulk
    s_elbow = geom.D / N_elbow
    s_theta = math.pi * geom.D / cfg.N_theta

    # Suggested size at elbow wall: most restrictive between elbow and circumference
    s_wall_elbow = min(s_elbow, s_theta)
    # For straight sections, use s_bulk as base
    s_wall_straight = s_bulk

    # --- NETGEN 3D parameters ---
    max_size = s_bulk
    min_size = s_bulk / 3.0
    growth_rate = cfg.growth_rate

    netgen_params = Netgen3DParams(
        max_size=max_size,
        min_size=min_size,
        growth_rate=growth_rate,
    )

    # --- 1D segments at inlet/outlet ---
    if geom.L_in > 0:
        N_in_raw = int(math.ceil(geom.L_in / s_bulk))
    else:
        N_in_raw = 0

    if geom.L_out > 0:
        N_out_raw = int(math.ceil(geom.L_out / s_bulk))
    else:
        N_out_raw = 0

    N_in = min(N_in_raw, cfg.N_in_max) if N_in_raw > 0 else 0
    N_out = min(N_out_raw, cfg.N_out_max) if N_out_raw > 0 else 0

    if N_in_raw > cfg.N_in_max:
        notes.append(
            f"Computed N_in = {N_in_raw} > N_in_max = {cfg.N_in_max}. "
            f"Clamped to {cfg.N_in_max}."
        )
    if N_out_raw > cfg.N_out_max:
        notes.append(
            f"Computed N_out = {N_out_raw} > N_out_max = {cfg.N_out_max}. "
            f"Clamped to {cfg.N_out_max}."
        )

    # --- 1D segments along elbow arc ---
    L_arc = math.radians(geom.theta_deg) * geom.R
    if L_arc > 0:
        N_arc_raw = int(math.ceil(L_arc / s_elbow))
    else:
        N_arc_raw = 0

    # Minimum number of arc segments by level + adjustment for small R/D
    N_arc_min = cfg.N_arc_min
    if r_over_d < 1.2 and geom.theta_deg >= 45.0:
        # Rather tight elbow: slightly increase the minimum
        N_arc_min = int(math.ceil(1.5 * N_arc_min))
        notes.append(
            f"Elbow with R/D = {r_over_d:.2f} < 1.2 and theta = {geom.theta_deg:.1f}°. "
            f"Minimum arc segments increased to {N_arc_min}."
        )

    if N_arc_raw > 0:
        N_arc = max(N_arc_raw, N_arc_min)
    else:
        N_arc = 0

    segments = OneDParams(
        N_in=N_in,
        N_out=N_out,
        N_arc=N_arc,
        N_in_raw=N_in_raw,
        N_out_raw=N_out_raw,
        N_arc_raw=N_arc_raw,
    )

    # --- Viscous layer ---
    total_thickness = cfg.viscous_total_thickness_factor * geom.D
    viscous = ViscousLayerParams(
        total_thickness=total_thickness,
        number_of_layers=cfg.viscous_layers,
        stretch_factor=cfg.viscous_stretch,
    )

    # --- Local sizes ---
    local = LocalSizeParams(
        s_bulk=s_bulk,
        s_elbow=s_elbow,
        s_theta=s_theta,
        s_wall_elbow=s_wall_elbow,
        s_wall_straight=s_wall_straight,
    )

    # --- NETGEN "Arguments" parameters ---
    # Chordal Error is scaled with elbow wall cell size.
    chordal_error = cfg.chordal_error_factor * s_wall_elbow

    netgen_args = NetgenArgumentsParams(
        fineness="Custom",
        nb_segs_per_edge=cfg.nb_segs_per_edge,
        nb_segs_per_radius=cfg.nb_segs_per_radius,
        chordal_error=chordal_error,
        limit_size_by_curvature=algo_cfg.limit_size_by_curvature,
        quad_dominated=algo_cfg.quad_dominated,
        second_order=algo_cfg.second_order,
        optimize=algo_cfg.optimize,
        main_3d_algorithm=algo_cfg.main_3d_algorithm,
        alternative_3d_algorithm=algo_cfg.alternative_3d_algorithm,
        alternative_2d_algorithm=algo_cfg.alt_2d_algorithm,
        alternative_1d_algorithm=algo_cfg.alt_1d_algorithm,
    )

    notes.append(
        "Reminder: 'Nb. Segs per Edge' and 'Nb. Segs per Radius' only take effect if "
        "'Limit Size by Surface Curvature' is enabled in the NETGEN hypothesis."
    )

    notes.append(
        "Check mesh quality in OpenFOAM (checkMesh): nonOrthogonality, skewness, "
        "aspect ratio, etc."
    )

    return MeshRecommendations(
        level=cfg.name,
        geometry=geom,
        netgen_3d=netgen_params,
        local_sizes=local,
        segments_1d=segments,
        viscous_layers=viscous,
        netgen_arguments=netgen_args,
        notes=notes,
    )
