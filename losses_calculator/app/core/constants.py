"""
Constantes físicas y valores por defecto para los cálculos de fricción.
"""


# Aceleración de la gravedad [m/s²]
G_DEFAULT: float = 9.81

# Agua a 20 °C (aprox.)
RHO_WATER_20C: float = 998.0      # kg/m³
MU_WATER_20C: float = 1.002e-3    # Pa·s

# Rugosidad típica para tubería de HDPE
EPSILON_HDPE_DEFAULT: float = 1.0e-5  # m (≈ 0.01 mm)


# (Por si quieres ampliar a más materiales)
MATERIAL_ROUGHNESS = {
    "HDPE": EPSILON_HDPE_DEFAULT,
}
