from dataclasses import dataclass


@dataclass(frozen=True)
class LevelConfig:
    # Config ligada al "nivel" de malla (coarse / medium / fine)
    name: str
    N_bulk: int                         # celdas por D en sentido axial (tramos rectos)
    N_theta: int                        # celdas alrededor de la circunferencia
    N_arc_min: int                      # mínimo de segmentos en el arco del codo
    N_in_max: int                       # máximo segmentos tramo de entrada
    N_out_max: int                      # máximo segmentos tramo de salida
    growth_rate: float                  # NETGEN growth rate
    viscous_total_thickness_factor: float  # fracción de D para espesor total de capa viscosa
    viscous_layers: int                 # número de capas prismáticas
    viscous_stretch: float              # factor de estiramiento entre capas prismáticas
    nb_segs_per_edge: int               # Nb. Segs per Edge (cuando se use curvatura)
    nb_segs_per_radius: int             # Nb. Segs per Radius (cuando se use curvatura)
    chordal_error_factor: float         # factor * s_wall_elbow → Chordal Error [m]


@dataclass(frozen=True)
class AlgorithmConfig:
    # Recomendación general de algoritmos para Salome
    main_3d_algorithm: str              # p.ej. "NETGEN 1D-2D-3D"
    alternative_3d_algorithm: str       # p.ej. "NETGEN 3D"
    alt_2d_algorithm: str               # p.ej. "NETGEN 2D (simple parameters)"
    alt_1d_algorithm: str               # p.ej. "Wire Discretization"
    limit_size_by_curvature: bool       # marcar / desmarcar "Limit Size by Surface Curvature"
    quad_dominated: bool                # marcar / desmarcar "Quad-dominated"
    second_order: bool                  # marcar / desmarcar "Second Order"
    optimize: bool                      # marcar / desmarcar "Optimize"


LEVEL_CONFIGS = {
    "coarse": LevelConfig(
        name="coarse",
        N_bulk=6,
        N_theta=32,
        N_arc_min=20,
        N_in_max=150,
        N_out_max=150,
        growth_rate=0.40,
        viscous_total_thickness_factor=0.03,
        viscous_layers=8,
        viscous_stretch=1.25,
        nb_segs_per_edge=1,
        nb_segs_per_radius=4,
        chordal_error_factor=0.30,
    ),
    "medium": LevelConfig(
        name="medium",
        N_bulk=10,
        N_theta=48,
        N_arc_min=36,
        N_in_max=250,
        N_out_max=250,
        growth_rate=0.35,
        viscous_total_thickness_factor=0.05,
        viscous_layers=10,
        viscous_stretch=1.20,
        nb_segs_per_edge=2,
        nb_segs_per_radius=6,
        chordal_error_factor=0.20,
    ),
    "fine": LevelConfig(
        name="fine",
        N_bulk=15,
        N_theta=64,
        N_arc_min=48,
        N_in_max=400,
        N_out_max=400,
        growth_rate=0.30,
        viscous_total_thickness_factor=0.07,
        viscous_layers=14,
        viscous_stretch=1.15,
        nb_segs_per_edge=3,
        nb_segs_per_radius=8,
        chordal_error_factor=0.15,
    ),
}


ALGORITHM_CONFIG = AlgorithmConfig(
    # Para un codo 3D típico que va a OpenFOAM:
    main_3d_algorithm="NETGEN 1D-2D-3D",
    alternative_3d_algorithm="NETGEN 3D",
    alt_2d_algorithm="NETGEN 2D (simple parameters)",
    alt_1d_algorithm="Wire Discretization",
    # Recomendación de checkboxes:
    # - Limit Size by Surface Curvature: por defecto OFF (controlas la malla con Max/Min y Local Sizes).
    # - Quad-dominated: OFF (triángulos en superficie suelen ir mejor con export a OpenFOAM).
    # - Second Order: OFF (OpenFOAM espera elementos de primer orden en el .unv).
    # - Optimize: ON (mejor calidad de elementos, aunque tarde un poco más).
    limit_size_by_curvature=False,
    quad_dominated=False,
    second_order=False,
    optimize=True,
)


def get_level_config(name: str) -> LevelConfig:
    """
    Devuelve la configuración para un nivel de mallado dado.
    Acepta mayúsculas/minúsculas y recorta espacios.
    """
    if not isinstance(name, str):
        raise ValueError(f"Nivel inválido: {name!r}")

    key = name.strip().lower()
    if key not in LEVEL_CONFIGS:
        valid = ", ".join(LEVEL_CONFIGS.keys())
        raise ValueError(f"Nivel desconocido '{name}'. Usa uno de: {valid}")
    return LEVEL_CONFIGS[key]


def get_algorithm_config() -> AlgorithmConfig:
    """
    Devuelve la configuración general recomendada de algoritmos NETGEN.
    """
    return ALGORITHM_CONFIG
