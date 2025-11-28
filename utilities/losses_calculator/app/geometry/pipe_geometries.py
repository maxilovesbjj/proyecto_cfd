from dataclasses import dataclass


@dataclass
class PipeSegment:
    """
    Representa un tramo de tubería recta de sección circular.
    Represents a straight circular pipe segment.

    Parameters
    ----------
    length_m : float
        Longitud del tramo [m].
        Segment length [m].

    diameter_m : float
        Diámetro interno de la tubería [m].
        Internal pipe diameter [m].

    roughness_m : float
        Rugosidad absoluta de la pared [m].
        Absolute wall roughness [m].

    name : str, optional
        Nombre descriptivo del tramo (para imprimir resultados).
        Descriptive name for reporting/printing.
    """

    length_m: float
    diameter_m: float
    roughness_m: float
    name: str = ""  # opcional / optional, only for display

    def __post_init__(self) -> None:
        """
        Validación básica de los parámetros geométricos.
        Basic validation of geometric parameters.
        """
        if self.length_m <= 0:
            raise ValueError(
                "Segment length must be > 0 "
                "(la longitud del tramo debe ser > 0)."
            )
        if self.diameter_m <= 0:
            raise ValueError(
                "Pipe diameter must be > 0 "
                "(el diámetro del tramo debe ser > 0)."
            )
        if self.roughness_m < 0:
            raise ValueError(
                "Roughness cannot be negative "
                "(la rugosidad del tramo no puede ser negativa)."
            )
