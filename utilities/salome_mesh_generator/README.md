# salome_mesh_generator

CLI helper to generate **mesh parameter recommendations** for Salome/NETGEN
for 3D pipe elbows (D, L_in, L_out, R, theta) at different mesh levels
(coarse / medium / fine).  
Asistente de línea de comandos para generar **parámetros de mallado** en
Salome/NETGEN para codos 3D (D, L_in, L_out, R, theta) con distintos niveles
de malla (coarse / medium / fine).

## Features / Características

- Interactive wizard to define elbow geometry and mesh level
- Recommended NETGEN 3D parameters (Max/Min Size, growth rate)
- Suggested `Local Sizes` for elbow wall and straight pipe sections
- 1D segment counts for inlet, outlet and elbow arc
- Viscous layer parameters for NETGEN 3D
- Bilingual CLI: **English / Español**
- Optional JSON output mode for automation (`--json`)

## Installation / Instalación

Requirements:

- Python 3.10+
- No external runtime dependencies (only Python standard library)

Clone the main repository:

```bash
git clone https://github.com/maxilovesbjj/proyecto_cfd.git
cd proyecto_cfd/utilities/salome_mesh_generator
