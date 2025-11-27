#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import math
from pathlib import Path

import numpy as np


# ==========================
# 1) TU MODELO TEÓRICO
# ==========================

def friction_factor(Re, eps_rel=0.0, model="auto"):
    """
    Calcula el factor de fricción de Darcy.

    Parámetros:
        Re      : número de Reynolds [-]
        eps_rel : rugosidad relativa ε/D [-] (0 para tubería lisa)
        model   : "auto", "laminar", "blasius", "haaland"
    """

    if Re <= 0:
        raise ValueError("Re debe ser > 0")

    model = model.lower()

    if model == "auto":
        if Re < 2300:
            return 64.0 / Re
        elif Re <= 1e5 and eps_rel <= 1e-5:
            return 0.3164 * Re ** -0.25
        else:
            model = "haaland"

    if model == "laminar":
        return 64.0 / Re

    elif model == "blasius":
        return 0.3164 * Re ** -0.25

    elif model == "haaland":
        # 1/sqrt(f) = -1.8 * log10[ ( (ε/D)/3.7 )^1.11 + 6.9/Re ]
        inv_sqrtf = -1.8 * math.log10((eps_rel / 3.7) ** 1.11 + 6.9 / Re)
        return 1.0 / inv_sqrtf ** 2

    else:
        raise ValueError(f"Modelo de fricción no reconocido: {model}")


def darcy_weisbach_dp(
    Q=None,
    U=None,
    D=0.35,
    L=10.0,
    rho=998.0,
    nu=1e-6,
    eps_rel=0.0,
    model="auto",
):
    """
    Darcy–Weisbach teórico para tubería circular.

    Devuelve dict con:
        A_m2, U_m_s, Q_m3_s, Re, f_Darcy, dp_Pa, dp_kPa, modelUsed.
    """

    A = math.pi * D ** 2 / 4.0

    if Q is None and U is None:
        raise ValueError("Debes entregar al menos Q o U.")

    if Q is not None:
        U = Q / A
    else:
        Q = U * A

    Re = U * D / nu
    f = friction_factor(Re, eps_rel=eps_rel, model=model)

    dp_Pa = f * (L / D) * 0.5 * rho * U ** 2
    dp_kPa = dp_Pa / 1000.0

    return {
        "A_m2": A,
        "U_m_s": U,
        "Q_m3_s": Q,
        "Re": Re,
        "f_Darcy": f,
        "dp_Pa": dp_Pa,
        "dp_kPa": dp_kPa,
        "modelUsed": model,
    }


# ==========================
# 2) FUNCIONES PARA LEER postProcessing
# ==========================

CASE_DIR = Path(__file__).resolve().parent
PP_DIR = CASE_DIR / "postProcessing"


def read_last_time_file(folder: Path, field_prefix: str):
    """
    Lee el ÚLTIMO valor de un archivo en postProcessing.

    - folder: p.ej. postProcessing/patchAverage_inlet
    - field_prefix: prefijo del archivo, p.ej. "p" o "flowRate"

    Asume formato:
        time  value
    en columnas.
    """
    if not folder.exists():
        raise RuntimeError(f"No existe carpeta {folder}")

    # Muchos functionObjects de OpenFOAM crean subcarpetas por tiempo
    time_dirs = sorted([d for d in folder.iterdir() if d.is_dir()])

    if not time_dirs:
        # Otras veces escriben un .dat directo en la carpeta
        files = sorted(folder.glob(f"{field_prefix}*"))
        if not files:
            raise RuntimeError(f"No hay archivos {field_prefix}* en {folder}")
        data = np.loadtxt(files[0])
        t, val = data[-1]
        return float(t), float(val)

    last_dir = time_dirs[-1]
    files = sorted(last_dir.glob(f"{field_prefix}*"))
    if not files:
        raise RuntimeError(f"No hay archivos {field_prefix}* en {last_dir}")
    data = np.loadtxt(files[0])
    t, val = data[-1]
    return float(t), float(val)


# ==========================
# 3) MAIN: LEE CFD + HACE TEORÍA + IMPRIME REPORTE
# ==========================

def main():
    # Parámetros del caso
    L = 20.0       # longitud CFD [m]
    D = 0.35       # "diámetro" hidráulico [m]
    rho = 998.0    # agua [kg/m3]
    nu = 1e-6      # [m2/s]
    eps_rel = 0.0  # rugosidad relativa (tubería lisa ideal)
    model = "auto" # modelo de fricción

    print("==============================================")
    print("  Post-proceso CFD caso pipe20m (consola)")
    print("==============================================")
    print(f"Directorio del caso : {CASE_DIR}")
    print(f"Longitud L          : {L:.3f} m")
    print(f'D "hidráulico"      : {D:.3f} m')
    print(f"rho                 : {rho:.1f} kg/m3")
    print(f"nu                  : {nu:.2e} m2/s")
    print(f"eps_rel             : {eps_rel:.2e}")
    print(f"modelo teórico f    : {model}")
    print("")

    # 1) Leer p_promedio en inlet/outlet
    pIn_folder = PP_DIR / "patchAverage_inlet"
    pOut_folder = PP_DIR / "patchAverage_outlet"

    t_in, p_in = read_last_time_file(pIn_folder, "p")
    t_out, p_out = read_last_time_file(pOut_folder, "p")

    dp_cfd = p_in - p_out
    dp_per_m_cfd = dp_cfd / L

    print("----- Presiones medias CFD (patchAverage) -----")
    print(f"t_in    [s]      : {t_in:.3f}")
    print(f"t_out   [s]      : {t_out:.3f}")
    print(f"p_in    [Pa]     : {p_in:.3f}")
    print(f"p_out   [Pa]     : {p_out:.3f}")
    print(f"Δp_20m  [Pa]     : {dp_cfd:.3f}")
    print(f"Δp/m    [Pa/m]   : {dp_per_m_cfd:.3f}")
    print("")

    # 2) Leer caudales CFD en inlet/outlet
    Qin_folder = PP_DIR / "patchFlowRate_inlet"
    Qout_folder = PP_DIR / "patchFlowRate_outlet"

    # Nota: en patchFlowRate el archivo suele llamarse algo tipo "flowRate.dat"
    t_Qin, Q_in = read_last_time_file(Qin_folder, "flowRate")
    t_Qout, Q_out = read_last_time_file(Qout_folder, "flowRate")

    print("----- Caudales CFD (patchFlowRate) -----")
    print(f"t_Qin   [s]      : {t_Qin:.3f}")
    print(f"t_Qout  [s]      : {t_Qout:.3f}")
    print(f"Q_in    [m3/s]   : {Q_in:.6f}")
    print(f"Q_out   [m3/s]   : {Q_out:.6f}")
    print("")

    # 3) Factor de fricción CFD (Darcy)
    #    Primero saco U media a partir de Q_in y área circular equivalente
    A_circ = math.pi * D ** 2 / 4.0
    U_cfd = Q_in / A_circ
    dynamic = 0.5 * rho * U_cfd ** 2
    f_cfd = dp_cfd * D / (L * dynamic)

    print("----- Magnitudes CFD derivadas -----")
    print(f"Área circ. eq. A  : {A_circ:.6f} m2")
    print(f"U_media_CFD       : {U_cfd:.4f} m/s")
    print(f"Factor fricción f : {f_cfd:.6f}")
    print("")

    # 4) Cálculo teórico usando TU función
    theory = darcy_weisbach_dp(
        Q=Q_in,
        D=D,
        L=L,
        rho=rho,
        nu=nu,
        eps_rel=eps_rel,
        model=model,
    )

    print("----- Teoría Darcy–Weisbach -----")
    print(f"Re_teo             : {theory['Re']:.3e}")
    print(f"f_teo (Darcy)      : {theory['f_Darcy']:.6f}")
    print(f"Δp_teo_20m [Pa]    : {theory['dp_Pa']:.3f}")
    print(f"Δp_teo_20m [kPa]   : {theory['dp_kPa']:.3f}")
    print(f"Δp_teo/m   [Pa/m]  : {theory['dp_Pa'] / L:.3f}")
    print(f"Modelo usado para f: {theory['modelUsed']}")
    print("")

    # 5) Errores relativos
    rel_dp = (dp_cfd - theory["dp_Pa"]) / theory["dp_Pa"] if theory["dp_Pa"] != 0 else float("nan")
    rel_f  = (f_cfd - theory["f_Darcy"]) / theory["f_Darcy"] if theory["f_Darcy"] != 0 else float("nan")

    print("----- Comparación CFD vs teoría -----")
    print(f"Error relativo Δp  : {rel_dp*100:.2f} %")
    print(f"Error relativo f   : {rel_f*100:.2f} %")
    print("==============================================")
    print("Listo. Estos son los números base para tu informe.")
    print("==============================================")


if __name__ == "__main__":
    main()
