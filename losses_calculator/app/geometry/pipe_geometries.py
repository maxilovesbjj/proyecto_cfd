from dataclasses import dataclass


@dataclass
class PipeSegment:
    """
    Representa un tramo de tubería recta de sección circular.
    """
    length_m: float
    diameter_m: float
    roughness_m: float
    name: str = ""  # opcional, solo para mostrar en pantalla

    def __post_init__(self) -> None:
        if self.length_m <= 0:
            raise ValueError("La longitud del tramo debe ser > 0.")
        if self.diameter_m <= 0:
            raise ValueError("El diámetro del tramo debe ser > 0.")
        if self.roughness_m < 0:
            raise ValueError("La rugosidad del tramo no puede ser negativa.")
