"""
Constantes físicas y valores por defecto para los cálculos de fricción.
Physical constants and default values for friction loss calculations.
"""

# Gravity acceleration [m/s²]
# Aceleración de la gravedad [m/s²]
G_DEFAULT: float = 9.81

# Water at 20 °C (approx.)
# Agua a 20 °C (aprox.)
RHO_WATER_20C: float = 998.0      # kg/m³
MU_WATER_20C: float = 1.002e-3    # Pa·s

# Typical roughness for HDPE pipe
# Rugosidad típica para tubería de HDPE
EPSILON_HDPE_DEFAULT: float = 1.0e-5  # m (≈ 0.01 mm)

# Dictionary of typical roughness values by material.
# Diccionario de rugosidades típicas por material.
MATERIAL_ROUGHNESS: dict[str, float] = {
    "HDPE": EPSILON_HDPE_DEFAULT,
    # Add more materials here if needed.
    # Agrega más materiales aquí si lo necesitas.
}
