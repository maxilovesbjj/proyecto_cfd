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
    """Datos de entrada geométricos y de nivel de malla."""
    D: float          # diámetro interno [m]
    L_in: float       # largo recto de entrada [m]
    L_out: float      # largo recto de salida [m]
    R: float          # radio del codo [m]
    theta_deg: float  # ángulo del codo [°]
    level: str        # coarse / medium / fine


@dataclass
class Netgen3DParams:
    max_size: float
    min_size: float
    growth_rate: float


@dataclass
class LocalSizeParams:
    s_bulk: float          # tamaño base en “bulk”
    s_elbow: float         # tamaño base asociado a N_elbow (≈ 2*N_bulk)
    s_theta: float         # tamaño alrededor de la circunferencia
    s_wall_elbow: float    # tamaño sugerido en elbow_wall
    s_wall_straight: float # tamaño sugerido en tramos rectos (opcional)


@dataclass
class OneDParams:
    N_in: int
    N_out: int
    N_arc: int
    N_in_raw: int
    N_out_raw: int
    N_arc_raw: int


@dataclass
class ViscousLayerParams:
    total_thickness: float
    number_of_layers: int
    stretch_factor: float


@dataclass
class NetgenArgumentsParams:
    """
    Parámetros específicos de la pestaña 'Arguments' de NETGEN 1D-2D-3D
    (o NETGEN 3D), más la recomendación de algoritmos.
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
    level: str
    geometry: GeometryInput
    netgen_3d: Netgen3DParams
    local_sizes: LocalSizeParams
    segments_1d: OneDParams
    viscous_layers: ViscousLayerParams
    netgen_arguments: NetgenArgumentsParams
    notes: List[str]

    def to_dict(self) -> Dict[str, Any]:
        """Convierte todo a un dict (útil para JSON)."""
        return asdict(self)


def _validate_geometry(g: GeometryInput) -> None:
    if g.D <= 0:
        raise ValueError("El diámetro D debe ser > 0.")
    if g.R <= 0:
        raise ValueError("El radio de codo R debe ser > 0.")
    if g.theta_deg <= 0:
        raise ValueError("El ángulo del codo theta debe ser > 0.")
    if g.L_in < 0 or g.L_out < 0:
        raise ValueError("Los largos L_in y L_out no pueden ser negativos.")


def compute_mesh_recommendations(geom: GeometryInput) -> MeshRecommendations:
    """
    Calcula los parámetros recomendados de mallado para Salome/NETGEN
    a partir de la geometría y del nivel de malla.
    """
    _validate_geometry(geom)

    cfg: LevelConfig = get_level_config(geom.level)
    algo_cfg: AlgorithmConfig = get_algorithm_config()
    notes: List[str] = []

    # Razón R/D (codos más "cerrados" necesitan más cariño)
    r_over_d = geom.R / geom.D

    # --- Tamaños base ---
    N_bulk = cfg.N_bulk
    N_elbow = 2 * N_bulk            # regla: codo ≈ 2 x resolución axial de bulk
    s_bulk = geom.D / N_bulk
    s_elbow = geom.D / N_elbow
    s_theta = math.pi * geom.D / cfg.N_theta

    # Tamaño sugerido en pared del codo: el más restrictivo de elbow y circunferencia
    s_wall_elbow = min(s_elbow, s_theta)
    # Para tramos rectos, usamos s_bulk como base
    s_wall_straight = s_bulk

    # --- Parámetros NETGEN 3D ---
    max_size = s_bulk
    min_size = s_bulk / 3.0
    growth_rate = cfg.growth_rate

    netgen_params = Netgen3DParams(
        max_size=max_size,
        min_size=min_size,
        growth_rate=growth_rate,
    )

    # --- Segmentos 1D en entrada/salida ---
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
            f"N_in calculado = {N_in_raw} > N_in_max={cfg.N_in_max}. "
            f"Se ha limitado a {cfg.N_in_max}."
        )
    if N_out_raw > cfg.N_out_max:
        notes.append(
            f"N_out calculado = {N_out_raw} > N_out_max={cfg.N_out_max}. "
            f"Se ha limitado a {cfg.N_out_max}."
        )

    # --- Segmentos 1D en el arco del codo ---
    L_arc = math.radians(geom.theta_deg) * geom.R
    if L_arc > 0:
        N_arc_raw = int(math.ceil(L_arc / s_elbow))
    else:
        N_arc_raw = 0

    # Mínimo de segmentos en arco según nivel + ajuste si R/D es pequeño
    N_arc_min = cfg.N_arc_min
    if r_over_d < 1.2 and geom.theta_deg >= 45.0:
        # codo bastante "cerrado": subimos un poco el mínimo
        N_arc_min = int(math.ceil(1.5 * N_arc_min))
        notes.append(
            f"Codo con R/D={r_over_d:.2f} < 1.2 y theta={geom.theta_deg:.1f}°. "
            f"Mínimo de segmentos en arco aumentado a {N_arc_min}."
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

    # --- Capa viscosa ---
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

    # --- Parámetros de la pestaña "Arguments" de NETGEN ---
    # Chordal Error se escala con el tamaño de celda en el codo.
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
        "Recuerda: Nb. Segs per Edge y Nb. Segs per Radius solo influyen "
        "si activas 'Limit Size by Surface Curvature' en la hipótesis NETGEN."
    )

    # Notas generales para recordarte el post-proceso en OpenFOAM
    notes.append(
        "Revisa la calidad de malla en OpenFOAM (checkMesh): "
        "nonOrthogonality, skewness, aspect ratio, etc."
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
