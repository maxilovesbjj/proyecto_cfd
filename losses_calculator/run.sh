#!/bin/bash

# Ruta absoluta del backend
BACKEND_DIR="/home/flavio/proyecto_cfd/losses_calculator"

# Entrar al backend
cd "$BACKEND_DIR" || {
    echo "ERROR: No se pudo entrar al directorio $BACKEND_DIR"
    exit 1
}

# Ejecutar la CLI del proyecto
python3 -m app.cli.main_cli
