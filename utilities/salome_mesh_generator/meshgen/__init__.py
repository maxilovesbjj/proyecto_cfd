"""
Paquete meshgen: calculadora de parámetros de mallado para Salome/NETGEN.

Expuesto:
- compute_mesh_recommendations
- GeometryInput
"""

from .calculator import compute_mesh_recommendations, GeometryInput

__all__ = ["compute_mesh_recommendations", "GeometryInput"]

__version__ = "0.1.0"
