"""
CLI para calcular pérdidas de carga por fricción en tuberías
usando correlaciones de Blasius o Haaland.

Flujo de la CLI:
  1) Eliges tipo de problema (tubería recta / con codo)
  2) Ingresas D y v -> se calcula Q
  3) Se calcula Re con agua a 20 °C y se muestra el régimen
  4) A partir de ese Re eliges Blasius o Haaland
  5) Luego se piden longitudes, rugosidad y tipo de codo (si aplica)

Extras:
  - Codos según tu tabla:
        Codo 90° SR (≈1D)   -> K = 0.75
        Codo 90° LR (≈1,5D) -> K = 0.45
        Codo 45° SR (≈1D)   -> K = 0.35
        Codo 45° LR (≈1,5D) -> K = 0.20
  - Rugosidad:
        1) HDPE típico
        2) Manual [mm]
        3) 0 (tubería lisa)
  - En cualquier pregunta:
        * 'm' o 'menu'         -> volver al menú principal
        * 'q', 'salir', 'exit' -> salir del programa

Ejemplo de uso desde la raíz del proyecto:

    cd /home/flavio/proyecto_cfd/backend
    python3 -m app.cli.main_cli
"""

import math
from typing import List, Tuple, Optional

from app.core.constants import (
    RHO_WATER_20C,
    MU_WATER_20C,
    EPSILON_HDPE_DEFAULT,
    G_DEFAULT,
)
from app.core.correlations import CorrelationMethod, classify_regime
from app.core.local_losses import get_elbow_k, get_elbow_label
from app.geometry.pipe_geometries import PipeSegment
from app.services.friction_service import (
    compute_single_segment_head_loss,
    compute_reynolds,
)


# ==========================
# Excepciones de control
# ==========================


class GoToMainMenu(Exception):
    """Señal para volver al menú principal."""
    pass


class QuitProgram(Exception):
    """Señal para terminar el programa."""
    pass


# ==========================
# Utilidades de entrada
# ==========================


def _check_special(raw: str) -> None:
    """
    Revisa si el usuario quiere volver al menú o salir.
    - 'm', 'menu'          -> GoToMainMenu
    - 'q', 'salir', 'exit' -> QuitProgram
    """
    text = raw.strip().lower()
    if text in {"m", "menu"}:
        raise GoToMainMenu()
    if text in {"q", "salir", "exit"}:
        raise QuitProgram()


def _ask_float(prompt: str, min_value: Optional[float] = None) -> float:
    while True:
        raw = input(prompt).strip()
        _check_special(raw)
        try:
            value = float(raw)
            if min_value is not None and value <= min_value:
                print(f"  Valor debe ser > {min_value}. Intente nuevamente.")
                continue
            return value
        except ValueError:
            print("  Entrada no válida, por favor ingrese un número.")


def _ask_int(prompt: str, min_value: Optional[int] = None) -> int:
    while True:
        raw = input(prompt).strip()
        _check_special(raw)
        try:
            value = int(raw)
            if min_value is not None and value < min_value:
                print(f"  Valor debe ser >= {min_value}. Intente nuevamente.")
                continue
            return value
        except ValueError:
            print("  Entrada no válida, por favor ingrese un número entero.")


# ==========================
# Selección de opciones
# ==========================


def _select_geometry_option() -> str:
    print("\n¿Qué desea calcular?")
    print("  1) Tubería recta sin codos")
    print("  2) Tubería recta con un codo")
    print("  3) Salir")
    while True:
        choice = input("Opción [1/2/3]: ").strip()
        _check_special(choice)
        if choice in {"1", "2", "3"}:
            return choice
        print("  Opción no válida, intente nuevamente.")


def _select_elbow_type() -> Tuple[str, float, str]:
    """
    Permite elegir el tipo de codo.
    Devuelve: (code, K, label)

    code coincide con app.core.local_losses.ELBOWS:
      - "elbow_90_SR"
      - "elbow_90_LR"
      - "elbow_45_SR"
      - "elbow_45_LR"
    """
    print("\nSeleccione el tipo de codo:")
    print("  1) Codo 90° SR (≈1D)")
    print("  2) Codo 90° LR (≈1,5D)")
    print("  3) Codo 45° SR (≈1D)")
    print("  4) Codo 45° LR (≈1,5D)")
    while True:
        choice = input("Opción [1/2/3/4]: ").strip()
        _check_special(choice)
        if choice == "1":
            code = "elbow_90_SR"
        elif choice == "2":
            code = "elbow_90_LR"
        elif choice == "3":
            code = "elbow_45_SR"
        elif choice == "4":
            code = "elbow_45_LR"
        else:
            print("  Opción no válida, intente nuevamente.")
            continue

        K = get_elbow_k(code)
        label = get_elbow_label(code)
        return code, K, label


def _select_correlation_method(Re: float) -> CorrelationMethod:
    """
    Elige Blasius o Haaland después de mostrar el Re estimado.
    """
    regime = classify_regime(Re)
    print("\n=== Selección de correlación para f ===")
    print(f"Número de Reynolds estimado (con D_ref y v_ref): Re = {Re:.3e}")
    print(f"Régimen estimado: {regime}")

    # Sugerencia automática
    # - Turbulento y 4e3 < Re < 1e5 -> Blasius recomendado
    # - Resto -> Haaland recomendado
    if regime == "turbulento" and 4.0e3 <= Re <= 1.0e5:
        suggested = "1"  # Blasius
        print("Sugerencia: Blasius (tubería lisa, rango clásico de validez).")
    else:
        suggested = "2"  # Haaland
        print("Sugerencia: Haaland (más general, con o sin rugosidad).")

    print("\nSeleccione el método de correlación para flujo turbulento:")
    print("  1) Blasius")
    print("  2) Haaland")

    while True:
        choice = input(f"Opción [1/2, por defecto {suggested}]: ").strip()
        _check_special(choice)
        if choice == "":
            choice = suggested

        if choice == "1":
            return "blasius"
        elif choice == "2":
            return "haaland"
        else:
            print("  Opción no válida, intente nuevamente.")


# ==========================
# Entrada: D, v, Q, rugosidad
# ==========================


def _ask_reference_diameter_and_velocity() -> Tuple[float, float, float]:
    """
    Pide:
      - Diámetro interno de referencia [mm]
      - Velocidad media de referencia [m/s]

    Calcula:
      - Q [m³/s] = v * A

    Devuelve: (diameter_m, velocity_ms, q_m3s)
    """
    print("\nIngreso de datos hidráulicos principales (para definir el caudal):")
    print("  En cualquier pregunta, puede escribir 'm' para volver al menú o 'q' para salir.\n")

    raw_d = input("Diámetro interno de referencia [mm]: ").strip()
    _check_special(raw_d)
    try:
        diameter_mm = float(raw_d)
    except ValueError:
        print("  Entrada no válida, usando 0 -> se solicitará nuevamente.")
        diameter_mm = _ask_float("Diámetro interno de referencia [mm]: ", min_value=0.0)
    if diameter_mm <= 0:
        diameter_mm = _ask_float("Diámetro interno de referencia [mm]: ", min_value=0.0)

    diameter_m = diameter_mm / 1000.0

    velocity_ms = _ask_float("Velocidad media de referencia [m/s]: ", min_value=0.0)

    area_m2 = math.pi * (diameter_m ** 2) / 4.0
    q_m3s = velocity_ms * area_m2
    q_lps = q_m3s * 1000.0

    print(f"\n  Área interna A = {area_m2:.6e} m²")
    print(f"  => Caudal equivalente Q = {q_m3s:.6f} m³/s  ({q_lps:.3f} L/s)\n")

    return diameter_m, velocity_ms, q_m3s


def _ask_roughness() -> float:
    """
    Pide la rugosidad de la tubería.
    Opciones:
      1) Rugosidad típica HDPE
      2) Rugosidad manual (mm)
      3) Rugosidad = 0 (tubería lisa)
    """
    print("\nRugosidad de la tubería:")
    print(f"  1) HDPE típico (ε = {EPSILON_HDPE_DEFAULT:.2e} m)")
    print("  2) Ingresar rugosidad absoluta manualmente [mm]")
    print("  3) Rugosidad = 0 (tubería perfectamente lisa)")
    
    while True:
        opt_r = input("Opción [1/2/3, por defecto 1]: ").strip()
        _check_special(opt_r)

        if opt_r == "" or opt_r == "1":
            return EPSILON_HDPE_DEFAULT
        elif opt_r == "2":
            eps_mm = _ask_float("Rugosidad absoluta [mm]: ", min_value=0.0)
            return eps_mm / 1000.0
        elif opt_r == "3":
            return 0.0
        else:
            print("  Opción no válida, intente nuevamente.")


def _ask_pipe_segment(index: int, default_diameter_m: Optional[float] = None) -> PipeSegment:
    """
    Pide los datos de un tramo:
      - nombre (opcional)
      - diámetro interno [mm] (con opción de usar el diámetro de referencia)
      - longitud [m]
      - rugosidad
    """
    print(f"\n=== Datos del tramo {index} ===")
    name = input("Nombre del tramo (opcional): ").strip()
    _check_special(name)

    if default_diameter_m is not None:
        default_mm = default_diameter_m * 1000.0
        prompt = f"Diámetro interno [mm] (ENTER para usar {default_mm:.2f} mm): "
        while True:
            raw = input(prompt).strip()
            _check_special(raw)
            if raw == "":
                diameter_m = default_diameter_m
                break
            try:
                diameter_mm = float(raw)
                if diameter_mm <= 0:
                    print("  El diámetro debe ser > 0. Intente nuevamente.")
                    continue
                diameter_m = diameter_mm / 1000.0
                break
            except ValueError:
                print("  Entrada no válida, por favor ingrese un número.")
    else:
        diameter_mm = _ask_float("Diámetro interno [mm]: ", min_value=0.0)
        diameter_m = diameter_mm / 1000.0

    length_m = _ask_float("Longitud del tramo [m]: ", min_value=0.0)
    roughness_m = _ask_roughness()

    return PipeSegment(
        length_m=length_m,
        diameter_m=diameter_m,
        roughness_m=roughness_m,
        name=name,
    )


# ==========================
# Impresión de resultados
# ==========================


def _print_single_result(
    q_m3s: float,
    segment: PipeSegment,
    method: CorrelationMethod,
    rho: float,
    mu: float,
    g: float,
) -> None:
    res = compute_single_segment_head_loss(
        q_m3s=q_m3s,
        segment=segment,
        rho=rho,
        mu=mu,
        g=g,
        method=method,
    )

    q_lps = q_m3s * 1000.0

    print("\n===== RESULTADOS: TUBERÍA RECTA SIN CODO =====")
    print(f"Caudal (a partir de D y v): {q_m3s:.6f} m³/s  ({q_lps:.3f} L/s)")
    print(f"Método:       {method.upper()}")
    print(f"Fluido:       agua a 20 °C (ρ={rho:.1f} kg/m³, μ={mu:.3e} Pa·s)")
    print(f"Gravedad g:   {g:.3f} m/s²\n")

    print("Geometría del tramo:")
    print(f"  Nombre:     {segment.name or '(sin nombre)'}")
    print(f"  Longitud:   {segment.length_m:.3f} m")
    print(f"  Diámetro:   {segment.diameter_m*1000.0:.2f} mm")
    print(f"  Rugosidad:  {segment.roughness_m*1000.0:.4f} mm\n")

    print("Magnitudes calculadas:")
    print(f"  Área interna A:        {res['area_m2']:.6e} m²")
    print(f"  Velocidad media v:     {res['velocity_ms']:.4f} m/s")
    print(f"  Reynolds Re:           {res['reynolds']:.2e}")
    print(f"  Régimen de flujo:      {res['regime']}")
    print(f"  f (Darcy-Weisbach):    {res['friction_factor']:.6f}")
    print(f"  hf (pérdida de carga): {res['hf_m']:.4f} m")
    print(f"  ΔP:                    {res['delta_p_pa']:.2f} Pa "
          f"({res['delta_p_bar']:.4f} bar)")
    print("==============================================\n")


def _handle_pipe_with_elbow_case(
    q_m3s: float,
    ref_diameter_m: float,
    method: CorrelationMethod,
    rho: float,
    mu: float,
    g: float,
) -> None:
    """
    Caso: tubería recta con un codo entre L1 y L2.
    Se asume mismo diámetro en todo el tramo (el de referencia).
    """
    print("\n=== Datos de la tubería con codo ===")
    L1 = _ask_float("Longitud L1 antes del codo [m]: ", min_value=0.0)
    L2 = _ask_float("Longitud L2 después del codo [m]: ", min_value=0.0)

    roughness_m = _ask_roughness()
    code, K, label = _select_elbow_type()

    total_length = L1 + L2

    segment = PipeSegment(
        length_m=total_length,
        diameter_m=ref_diameter_m,
        roughness_m=roughness_m,
        name=f"Tubería con {label}",
    )

    fric = compute_single_segment_head_loss(
        q_m3s=q_m3s,
        segment=segment,
        rho=rho,
        mu=mu,
        g=g,
        method=method,
    )

    v = fric["velocity_ms"]
    head_velocity = v ** 2 / (2.0 * g)

    hf_elbow = K * head_velocity
    delta_p_elbow_pa = rho * g * hf_elbow
    delta_p_elbow_bar = delta_p_elbow_pa / 1.0e5

    hf_total = fric["hf_m"] + hf_elbow
    delta_p_total_pa = fric["delta_p_pa"] + delta_p_elbow_pa
    delta_p_total_bar = delta_p_total_pa / 1.0e5

    q_lps = q_m3s * 1000.0

    print("\n===== RESULTADOS: TUBERÍA CON CODO =====")
    print(f"Caudal (a partir de D y v): {q_m3s:.6f} m³/s  ({q_lps:.3f} L/s)")
    print(f"Método:       {method.upper()}")
    print(f"Fluido:       agua a 20 °C (ρ={rho:.1f} kg/m³, μ={mu:.3e} Pa·s)")
    print(f"Gravedad g:   {g:.3f} m/s²\n")

    print("Geometría:")
    print(f"  Diámetro ref.: {ref_diameter_m*1000.0:.2f} mm")
    print(f"  L1:            {L1:.3f} m")
    print(f"  L2:            {L2:.3f} m")
    print(f"  L total:       {total_length:.3f} m")
    print(f"  Rugosidad:     {roughness_m*1000.0:.4f} mm\n")

    print("Fricción en tubería (L1 + codo + L2):")
    print(f"  Área interna A:        {fric['area_m2']:.6e} m²")
    print(f"  Velocidad media v:     {fric['velocity_ms']:.4f} m/s")
    print(f"  Reynolds Re:           {fric['reynolds']:.2e}")
    print(f"  Régimen de flujo:      {fric['regime']}")
    print(f"  f (Darcy-Weisbach):    {fric['friction_factor']:.6f}")
    print(f"  hf fricción:           {fric['hf_m']:.4f} m")
    print(f"  ΔP fricción:           {fric['delta_p_pa']:.2f} Pa "
          f"({fric['delta_p_bar']:.4f} bar)\n")

    print("Pérdida localizada en el codo:")
    print(f"  Tipo de codo:          {label} (código {code})")
    print(f"  K teórico:             {K:.3f}")
    print(f"  hf codo:               {hf_elbow:.4f} m")
    print(f"  ΔP codo:               {delta_p_elbow_pa:.2f} Pa "
          f"({delta_p_elbow_bar:.4f} bar)\n")

    print("Totales (fricción + codo):")
    print(f"  hf total:              {hf_total:.4f} m")
    print(f"  ΔP total:              {delta_p_total_pa:.2f} Pa "
          f"({delta_p_total_bar:.4f} bar)")
    print("=========================================\n")


# ==========================
# main()
# ==========================


def main() -> None:
    print("============================================")
    print("  Calculadora de pérdidas por fricción")
    print("  (Darcy-Weisbach, Blasius / Haaland)")
    print("============================================")
    print("  En cualquier pregunta:")
    print("    - 'm' o 'menu'          -> volver al menú principal")
    print("    - 'q', 'salir', 'exit'  -> salir\n")

    rho = RHO_WATER_20C
    mu = MU_WATER_20C
    g = G_DEFAULT

    while True:
        try:
            geom_opt = _select_geometry_option()
            if geom_opt == "3":
                print("Saliendo... ¡hasta luego!")
                break

            # 1) D y v -> Q
            ref_diameter_m, ref_velocity_ms, q_m3s = _ask_reference_diameter_and_velocity()

            # 2) Calcular Re estimado y mostrar régimen
            Re_ref = compute_reynolds(
                velocity_ms=ref_velocity_ms,
                diameter_m=ref_diameter_m,
                rho=rho,
                mu=mu,
            )
            regime_ref = classify_regime(Re_ref)
            print(f"Re estimado con D_ref y v_ref: Re = {Re_ref:.3e} ({regime_ref})")

            # 3) Elegir método en base a ese Re
            method = _select_correlation_method(Re_ref)

            # 4) Resolver problema geométrico
            if geom_opt == "1":
                print("Se usará el diámetro de referencia para el tramo (puede modificarlo si desea).\n")
                seg = _ask_pipe_segment(1, default_diameter_m=ref_diameter_m)
                _print_single_result(q_m3s, seg, method, rho, mu, g)
            elif geom_opt == "2":
                _handle_pipe_with_elbow_case(q_m3s, ref_diameter_m, method, rho, mu, g)

        except GoToMainMenu:
            print("\nVolviendo al menú principal...\n")
            continue
        except QuitProgram:
            print("\nSaliendo... ¡hasta luego!")
            break


if __name__ == "__main__":
    main()
