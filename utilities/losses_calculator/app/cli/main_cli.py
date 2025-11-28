"""
CLI para calcular pérdidas de carga por fricción en tuberías
usando correlaciones de Blasius o Haaland.

CLI to compute head losses due to friction in pipes
using Blasius or Haaland correlations.

Flujo de la CLI / CLI flow:
  1) Eliges tipo de problema (tubería recta / con codo)
     You choose the problem type (straight pipe / pipe with elbow)
  2) Ingresas D y v -> se calcula Q
     You enter D and v -> Q is computed
  3) Se calcula Re con agua a 20 °C y se muestra el régimen
     Re is computed with water at 20 °C and the regime is shown
  4) A partir de ese Re eliges Blasius o Haaland
     Based on that Re, you choose Blasius or Haaland
  5) Luego se piden longitudes, rugosidad y tipo de codo (si aplica)
     Then lengths, roughness, and elbow type are requested (if applicable)

Extras:
  - Codos según tu tabla / Elbows according to your table:
        Codo 90° SR (≈1D)   -> K = 0.75
        Codo 90° LR (≈1,5D) -> K = 0.45
        Codo 45° SR (≈1D)   -> K = 0.35
        Codo 45° LR (≈1,5D) -> K = 0.20

  - Rugosidad / Roughness:
        1) HDPE típico / Typical HDPE
        2) Manual [mm] / Manual [mm]
        3) 0 (tubería lisa / smooth pipe)

  - En cualquier pregunta / At any prompt:
        * 'm' o 'menu' / 'main' / 'back'      -> volver al menú principal / go back to main menu
        * 'q', 'salir', 'exit', 'quit'       -> salir del programa / quit program

Ejemplo de uso / Example usage:

    cd /ruta/al/proyecto
    python3 -m app.cli.main_cli
"""

import math
from typing import Tuple, Optional

from app.core.constants import (
    RHO_WATER_20C,
    MU_WATER_20C,
    EPSILON_HDPE_DEFAULT,
    G_DEFAULT,
)
from app.core.correlations import CorrelationMethod, classify_regime
from app.core.local_losses import get_elbow_k
from app.geometry.pipe_geometries import PipeSegment
from app.services.friction_service import (
    compute_single_segment_head_loss,
    compute_reynolds,
)

# ==========================
# Idioma global / Global language
# ==========================

LANG: str = "es"  # "es" (español) / "en" (english)

# Mapas de etiquetas / Label maps

REGIME_LABELS = {
    "laminar": {"es": "laminar", "en": "laminar"},
    "transicion": {"es": "transición", "en": "transition"},
    "turbulento": {"es": "turbulento", "en": "turbulent"},
}

ELBOW_LABELS = {
    "elbow_90_SR": {
        "es": "Codo 90° SR (≈1D, radio corto)",
        "en": "90° SR elbow (≈1D, short radius)",
    },
    "elbow_90_LR": {
        "es": "Codo 90° LR (≈1,5D, radio largo)",
        "en": "90° LR elbow (≈1.5D, long radius)",
    },
    "elbow_45_SR": {
        "es": "Codo 45° SR (≈1D, radio corto)",
        "en": "45° SR elbow (≈1D, short radius)",
    },
    "elbow_45_LR": {
        "es": "Codo 45° LR (≈1,5D, radio largo)",
        "en": "45° LR elbow (≈1.5D, long radius)",
    },
}


def _set_language() -> None:
    """Pregunta idioma al usuario / Ask user for language."""
    global LANG
    print("============================================")
    print("Seleccionar idioma / Select language:")
    print("  1) Español")
    print("  2) English")
    while True:
        choice = input("Opción [1/2, por defecto 1 / default 1]: ").strip()
        if choice == "" or choice == "1":
            LANG = "es"
            print("\nIdioma seleccionado: Español\n")
            return
        elif choice == "2":
            LANG = "en"
            print("\nSelected language: English\n")
            return
        else:
            print("  Opción no válida / Invalid option, please try again.")


def _localize_regime(raw: str) -> str:
    """
    Convierte el código de régimen a texto según idioma.
    Converts regime code/text to localized label.
    """
    key = raw.strip().lower()
    # Normalizar posibles salidas de classify_regime (por si ya viene en español)
    if key in {"transitorio", "transición"}:
        key = "transicion"
    if key not in REGIME_LABELS:
        # Fallback: devolver tal cual
        return raw
    return REGIME_LABELS[key][LANG]


def _localize_elbow_label(code: str) -> str:
    """
    Devuelve etiqueta de codo según idioma.
    Returns elbow label according to language.
    """
    if code in ELBOW_LABELS:
        return ELBOW_LABELS[code][LANG]
    # Fallback: código puro
    return code


# ==========================
# Excepciones de control / Control-flow exceptions
# ==========================


class GoToMainMenu(Exception):
    """Señal para volver al menú principal / Signal to go back to main menu."""
    pass


class QuitProgram(Exception):
    """Señal para terminar el programa / Signal to quit the program."""
    pass


# ==========================
# Utilidades de entrada / Input helpers
# ==========================


def _check_special(raw: str) -> None:
    """
    Revisa si el usuario quiere volver al menú o salir.
    Check if the user wants to go back to main menu or quit.

    - 'm', 'menu', 'main', 'back'   -> GoToMainMenu
    - 'q', 'salir', 'exit', 'quit'  -> QuitProgram
    """
    text = raw.strip().lower()
    if text in {"m", "menu", "main", "back"}:
        raise GoToMainMenu()
    if text in {"q", "salir", "exit", "quit"}:
        raise QuitProgram()


def _ask_float(prompt_es: str, prompt_en: str, min_value: Optional[float] = None) -> float:
    """Pide un float con validación mínima / Ask for a float with optional min validation."""
    prompt = prompt_es if LANG == "es" else prompt_en
    while True:
        raw = input(prompt).strip()
        _check_special(raw)
        try:
            value = float(raw)
            if min_value is not None and value <= min_value:
                if LANG == "es":
                    print(f"  Valor debe ser > {min_value}. Intente nuevamente.")
                else:
                    print(f"  Value must be > {min_value}. Please try again.")
                continue
            return value
        except ValueError:
            if LANG == "es":
                print("  Entrada no válida, por favor ingrese un número.")
            else:
                print("  Invalid input, please enter a number.")


def _ask_int(prompt_es: str, prompt_en: str, min_value: Optional[int] = None) -> int:
    """Pide un entero con validación mínima / Ask for an int with optional min validation."""
    prompt = prompt_es if LANG == "es" else prompt_en
    while True:
        raw = input(prompt).strip()
        _check_special(raw)
        try:
            value = int(raw)
            if min_value is not None and value < min_value:
                if LANG == "es":
                    print(f"  Valor debe ser >= {min_value}. Intente nuevamente.")
                else:
                    print(f"  Value must be >= {min_value}. Please try again.")
                continue
            return value
        except ValueError:
            if LANG == "es":
                print("  Entrada no válida, por favor ingrese un número entero.")
            else:
                print("  Invalid input, please enter an integer.")


# ==========================
# Selección de opciones / Option selection
# ==========================


def _select_geometry_option() -> str:
    """Selecciona tipo de problema / Select problem type."""
    if LANG == "es":
        print("\n¿Qué desea calcular?")
        print("  1) Tubería recta sin codos")
        print("  2) Tubería recta con un codo")
        print("  3) Salir")
        prompt = "Opción [1/2/3]: "
        invalid = "  Opción no válida, intente nuevamente."
    else:
        print("\nWhat do you want to calculate?")
        print("  1) Straight pipe without elbows")
        print("  2) Straight pipe with one elbow")
        print("  3) Quit")
        prompt = "Option [1/2/3]: "
        invalid = "  Invalid option, please try again."

    while True:
        choice = input(prompt).strip()
        _check_special(choice)
        if choice in {"1", "2", "3"}:
            return choice
        print(invalid)


def _select_elbow_type() -> Tuple[str, float, str]:
    """
    Permite elegir el tipo de codo / Allows choosing elbow type.
    Devuelve / Returns: (code, K, label_localized)
    """
    if LANG == "es":
        print("\nSeleccione el tipo de codo:")
        print("  1) Codo 90° SR (≈1D)")
        print("  2) Codo 90° LR (≈1,5D)")
        print("  3) Codo 45° SR (≈1D)")
        print("  4) Codo 45° LR (≈1,5D)")
        prompt = "Opción [1/2/3/4]: "
        invalid = "  Opción no válida, intente nuevamente."
    else:
        print("\nSelect elbow type:")
        print("  1) 90° SR elbow (≈1D)")
        print("  2) 90° LR elbow (≈1.5D)")
        print("  3) 45° SR elbow (≈1D)")
        print("  4) 45° LR elbow (≈1.5D)")
        prompt = "Option [1/2/3/4]: "
        invalid = "  Invalid option, please try again."

    while True:
        choice = input(prompt).strip()
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
            print(invalid)
            continue

        K = get_elbow_k(code)
        label = _localize_elbow_label(code)
        return code, K, label


def _select_correlation_method(Re: float) -> CorrelationMethod:
    """
    Elige Blasius o Haaland después de mostrar el Re estimado.
    Choose Blasius or Haaland after showing the estimated Re.
    """
    regime_raw = classify_regime(Re)
    regime = _localize_regime(regime_raw)

    if LANG == "es":
        print("\n=== Selección de correlación para f ===")
        print(f"Número de Reynolds estimado (con D_ref y v_ref): Re = {Re:.3e}")
        print(f"Régimen estimado: {regime}")
    else:
        print("\n=== Correlation selection for f ===")
        print(f"Estimated Reynolds number (with D_ref and v_ref): Re = {Re:.3e}")
        print(f"Estimated regime: {regime}")

    # Sugerencia automática / Automatic suggestion
    if regime_raw == "turbulento" and 4.0e3 <= Re <= 1.0e5:
        suggested = "1"  # Blasius
        if LANG == "es":
            print("Sugerencia: Blasius (tubería lisa, rango clásico de validez).")
        else:
            print("Suggestion: Blasius (smooth pipe, classical validity range).")
    else:
        suggested = "2"  # Haaland
        if LANG == "es":
            print("Sugerencia: Haaland (más general, con o sin rugosidad).")
        else:
            print("Suggestion: Haaland (more general, with or without roughness).")

    if LANG == "es":
        print("\nSeleccione el método de correlación para flujo turbulento:")
        print("  1) Blasius")
        print("  2) Haaland")
        prompt = f"Opción [1/2, por defecto {suggested}]: "
        invalid = "  Opción no válida, intente nuevamente."
    else:
        print("\nSelect correlation method for turbulent flow:")
        print("  1) Blasius")
        print("  2) Haaland")
        prompt = f"Option [1/2, default {suggested}]: "
        invalid = "  Invalid option, please try again."

    while True:
        choice = input(prompt).strip()
        _check_special(choice)
        if choice == "":
            choice = suggested

        if choice == "1":
            return "blasius"
        elif choice == "2":
            return "haaland"
        else:
            print(invalid)


# ==========================
# Entrada: D, v, Q, rugosidad / Input: D, v, Q, roughness
# ==========================


def _ask_reference_diameter_and_velocity() -> Tuple[float, float, float]:
    """
    Pide / Asks for:
      - Diámetro interno de referencia [mm] / Reference internal diameter [mm]
      - Velocidad media de referencia [m/s] / Mean reference velocity [m/s]

    Calcula / Computes:
      - Q [m³/s] = v * A

    Devuelve / Returns: (diameter_m, velocity_ms, q_m3s)
    """
    if LANG == "es":
        print("\nIngreso de datos hidráulicos principales (para definir el caudal):")
        print("  En cualquier pregunta, puede escribir 'm' para volver al menú o 'q' para salir.\n")
        prompt_d = "Diámetro interno de referencia [mm]: "
        prompt_d_retry = "Diámetro interno de referencia [mm]: "
        prompt_v = "Velocidad media de referencia [m/s]: "
    else:
        print("\nInput of main hydraulic data (to define the flow rate):")
        print("  At any prompt, you can type 'm' to go back to menu or 'q' to quit.\n")
        prompt_d = "Reference internal diameter [mm]: "
        prompt_d_retry = "Reference internal diameter [mm]: "
        prompt_v = "Reference mean velocity [m/s]: "

    raw_d = input(prompt_d).strip()
    _check_special(raw_d)
    try:
        diameter_mm = float(raw_d)
    except ValueError:
        if LANG == "es":
            print("  Entrada no válida, usando 0 -> se solicitará nuevamente.")
        else:
            print("  Invalid input, using 0 -> will ask again.")
        diameter_mm = _ask_float(prompt_d_retry, prompt_d_retry, min_value=0.0)
    if diameter_mm <= 0:
        diameter_mm = _ask_float(prompt_d_retry, prompt_d_retry, min_value=0.0)

    diameter_m = diameter_mm / 1000.0
    velocity_ms = _ask_float(prompt_v, prompt_v, min_value=0.0)

    area_m2 = math.pi * (diameter_m ** 2) / 4.0
    q_m3s = velocity_ms * area_m2
    q_lps = q_m3s * 1000.0

    if LANG == "es":
        print(f"\n  Área interna A = {area_m2:.6e} m²")
        print(f"  => Caudal equivalente Q = {q_m3s:.6f} m³/s  ({q_lps:.3f} L/s)\n")
    else:
        print(f"\n  Internal area A = {area_m2:.6e} m²")
        print(f"  => Equivalent flow rate Q = {q_m3s:.6f} m³/s  ({q_lps:.3f} L/s)\n")

    return diameter_m, velocity_ms, q_m3s


def _ask_roughness() -> float:
    """
    Pide la rugosidad de la tubería / Asks for pipe roughness.
    Opciones / Options:
      1) Rugosidad típica HDPE / Typical HDPE roughness
      2) Rugosidad manual (mm) / Manual roughness (mm)
      3) Rugosidad = 0 (tubería lisa) / Roughness = 0 (perfectly smooth pipe)
    """
    if LANG == "es":
        print("\nRugosidad de la tubería:")
        print(f"  1) HDPE típico (ε = {EPSILON_HDPE_DEFAULT:.2e} m)")
        print("  2) Ingresar rugosidad absoluta manualmente [mm]")
        print("  3) Rugosidad = 0 (tubería perfectamente lisa)")
        prompt = "Opción [1/2/3, por defecto 1]: "
        invalid = "  Opción no válida, intente nuevamente."
        prompt_eps = "Rugosidad absoluta [mm]: "
    else:
        print("\nPipe roughness:")
        print(f"  1) Typical HDPE (ε = {EPSILON_HDPE_DEFAULT:.2e} m)")
        print("  2) Enter absolute roughness manually [mm]")
        print("  3) Roughness = 0 (perfectly smooth pipe)")
        prompt = "Option [1/2/3, default 1]: "
        invalid = "  Invalid option, please try again."
        prompt_eps = "Absolute roughness [mm]: "

    while True:
        opt_r = input(prompt).strip()
        _check_special(opt_r)

        if opt_r == "" or opt_r == "1":
            return EPSILON_HDPE_DEFAULT
        elif opt_r == "2":
            eps_mm = _ask_float(prompt_eps, prompt_eps, min_value=0.0)
            return eps_mm / 1000.0
        elif opt_r == "3":
            return 0.0
        else:
            print(invalid)


def _ask_pipe_segment(index: int, default_diameter_m: Optional[float] = None) -> PipeSegment:
    """
    Pide los datos de un tramo / Ask for a pipe segment:
      - nombre (opcional) / name (optional)
      - diámetro interno [mm] (o usa uno por defecto) / internal diameter [mm] (or default)
      - longitud [m] / length [m]
      - rugosidad / roughness
    """
    if LANG == "es":
        print(f"\n=== Datos del tramo {index} ===")
        prompt_name = "Nombre del tramo (opcional): "
        prompt_d = "Diámetro interno [mm]: "
        prompt_L = "Longitud del tramo [m]: "
        invalid_d = "  El diámetro debe ser > 0. Intente nuevamente."
        invalid_num = "  Entrada no válida, por favor ingrese un número."
    else:
        print(f"\n=== Segment {index} data ===")
        prompt_name = "Segment name (optional): "
        prompt_d = "Internal diameter [mm]: "
        prompt_L = "Segment length [m]: "
        invalid_d = "  Diameter must be > 0. Please try again."
        invalid_num = "  Invalid input, please enter a number."

    name = input(prompt_name).strip()
    _check_special(name)

    if default_diameter_m is not None:
        default_mm = default_diameter_m * 1000.0
        if LANG == "es":
            prompt = f"Diámetro interno [mm] (ENTER para usar {default_mm:.2f} mm): "
        else:
            prompt = f"Internal diameter [mm] (ENTER to use {default_mm:.2f} mm): "

        while True:
            raw = input(prompt).strip()
            _check_special(raw)
            if raw == "":
                diameter_m = default_diameter_m
                break
            try:
                diameter_mm = float(raw)
                if diameter_mm <= 0:
                    print(invalid_d)
                    continue
                diameter_m = diameter_mm / 1000.0
                break
            except ValueError:
                print(invalid_num)
    else:
        diameter_mm = _ask_float(prompt_d, prompt_d, min_value=0.0)
        diameter_m = diameter_mm / 1000.0

    length_m = _ask_float(prompt_L, prompt_L, min_value=0.0)
    roughness_m = _ask_roughness()

    return PipeSegment(
        length_m=length_m,
        diameter_m=diameter_m,
        roughness_m=roughness_m,
        name=name,
    )


# ==========================
# Impresión de resultados / Printing results
# ==========================


def _print_single_result(
    q_m3s: float,
    segment: PipeSegment,
    method: CorrelationMethod,
    rho: float,
    mu: float,
    g: float,
) -> None:
    """Imprime resultados para tubería recta / Print results for straight pipe."""
    res = compute_single_segment_head_loss(
        q_m3s=q_m3s,
        segment=segment,
        rho=rho,
        mu=mu,
        g=g,
        method=method,
    )

    q_lps = q_m3s * 1000.0
    regime_label = _localize_regime(res["regime"])

    if LANG == "es":
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
        print(f"  Régimen de flujo:      {regime_label}")
        print(f"  f (Darcy-Weisbach):    {res['friction_factor']:.6f}")
        print(f"  hf (pérdida de carga): {res['hf_m']:.4f} m")
        print(
            f"  ΔP:                    {res['delta_p_pa']:.2f} Pa "
            f"({res['delta_p_bar']:.4f} bar)"
        )
        print("==============================================\n")
    else:
        print("\n===== RESULTS: STRAIGHT PIPE WITHOUT ELBOW =====")
        print(f"Flow rate (from D and v): {q_m3s:.6f} m³/s  ({q_lps:.3f} L/s)")
        print(f"Method:       {method.upper()}")
        print(f"Fluid:        water at 20 °C (ρ={rho:.1f} kg/m³, μ={mu:.3e} Pa·s)")
        print(f"Gravity g:    {g:.3f} m/s²\n")

        print("Segment geometry:")
        print(f"  Name:        {segment.name or '(no name)'}")
        print(f"  Length:      {segment.length_m:.3f} m")
        print(f"  Diameter:    {segment.diameter_m*1000.0:.2f} mm")
        print(f"  Roughness:   {segment.roughness_m*1000.0:.4f} mm\n")

        print("Computed quantities:")
        print(f"  Internal area A:       {res['area_m2']:.6e} m²")
        print(f"  Mean velocity v:       {res['velocity_ms']:.4f} m/s")
        print(f"  Reynolds Re:           {res['reynolds']:.2e}")
        print(f"  Flow regime:           {regime_label}")
        print(f"  f (Darcy-Weisbach):    {res['friction_factor']:.6f}")
        print(f"  hf (head loss):        {res['hf_m']:.4f} m")
        print(
            f"  ΔP:                    {res['delta_p_pa']:.2f} Pa "
            f"({res['delta_p_bar']:.4f} bar)"
        )
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
    Case: straight pipe with one elbow between L1 and L2.
    """
    if LANG == "es":
        print("\n=== Datos de la tubería con codo ===")
        prompt_L1 = "Longitud L1 antes del codo [m]: "
        prompt_L2 = "Longitud L2 después del codo [m]: "
    else:
        print("\n=== Data for pipe with elbow ===")
        prompt_L1 = "Length L1 before the elbow [m]: "
        prompt_L2 = "Length L2 after the elbow [m]: "

    L1 = _ask_float(prompt_L1, prompt_L1, min_value=0.0)
    L2 = _ask_float(prompt_L2, prompt_L2, min_value=0.0)

    roughness_m = _ask_roughness()
    code, K, label = _select_elbow_type()

    total_length = L1 + L2
    seg_name = (
        f"Tubería con {label}" if LANG == "es" else f"Pipe with {label}"
    )

    segment = PipeSegment(
        length_m=total_length,
        diameter_m=ref_diameter_m,
        roughness_m=roughness_m,
        name=seg_name,
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
    regime_label = _localize_regime(fric["regime"])

    if LANG == "es":
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
        print(f"  Régimen de flujo:      {regime_label}")
        print(f"  f (Darcy-Weisbach):    {fric['friction_factor']:.6f}")
        print(f"  hf fricción:           {fric['hf_m']:.4f} m")
        print(
            f"  ΔP fricción:           {fric['delta_p_pa']:.2f} Pa "
            f"({fric['delta_p_bar']:.4f} bar)\n"
        )

        print("Pérdida localizada en el codo:")
        print(f"  Tipo de codo:          {label} (código {code})")
        print(f"  K teórico:             {K:.3f}")
        print(f"  hf codo:               {hf_elbow:.4f} m")
        print(
            f"  ΔP codo:               {delta_p_elbow_pa:.2f} Pa "
            f"({delta_p_elbow_bar:.4f} bar)\n"
        )

        print("Totales (fricción + codo):")
        print(f"  hf total:              {hf_total:.4f} m")
        print(
            f"  ΔP total:              {delta_p_total_pa:.2f} Pa "
            f"({delta_p_total_bar:.4f} bar)"
        )
        print("=========================================\n")
    else:
        print("\n===== RESULTS: PIPE WITH ELBOW =====")
        print(f"Flow rate (from D and v): {q_m3s:.6f} m³/s  ({q_lps:.3f} L/s)")
        print(f"Method:       {method.upper()}")
        print(f"Fluid:        water at 20 °C (ρ={rho:.1f} kg/m³, μ={mu:.3e} Pa·s)")
        print(f"Gravity g:    {g:.3f} m/s²\n")

        print("Geometry:")
        print(f"  Ref. diameter: {ref_diameter_m*1000.0:.2f} mm")
        print(f"  L1:            {L1:.3f} m")
        print(f"  L2:            {L2:.3f} m")
        print(f"  Total L:       {total_length:.3f} m")
        print(f"  Roughness:     {roughness_m*1000.0:.4f} mm\n")

        print("Friction in pipe (L1 + elbow + L2):")
        print(f"  Internal area A:       {fric['area_m2']:.6e} m²")
        print(f"  Mean velocity v:       {fric['velocity_ms']:.4f} m/s")
        print(f"  Reynolds Re:           {fric['reynolds']:.2e}")
        print(f"  Flow regime:           {regime_label}")
        print(f"  f (Darcy-Weisbach):    {fric['friction_factor']:.6f}")
        print(f"  hf friction:           {fric['hf_m']:.4f} m")
        print(
            f"  ΔP friction:           {fric['delta_p_pa']:.2f} Pa "
            f"({fric['delta_p_bar']:.4f} bar)\n"
        )

        print("Local loss at the elbow:")
        print(f"  Elbow type:            {label} (code {code})")
        print(f"  Theoretical K:         {K:.3f}")
        print(f"  hf elbow:              {hf_elbow:.4f} m")
        print(
            f"  ΔP elbow:              {delta_p_elbow_pa:.2f} Pa "
            f"({delta_p_elbow_bar:.4f} bar)\n"
        )

        print("Totals (friction + elbow):")
        print(f"  hf total:              {hf_total:.4f} m")
        print(
            f"  ΔP total:              {delta_p_total_pa:.2f} Pa "
            f"({delta_p_total_bar:.4f} bar)"
        )
        print("=========================================\n")


# ==========================
# main()
# ==========================


def main() -> None:
    """Punto de entrada principal / Main entry point."""
    _set_language()

    if LANG == "es":
        print("============================================")
        print("  Calculadora de pérdidas por fricción")
        print("  (Darcy-Weisbach, Blasius / Haaland)")
        print("============================================")
        print("  En cualquier pregunta:")
        print("    - 'm' o 'menu'          -> volver al menú principal")
        print("    - 'q', 'salir', 'exit'  -> salir\n")
    else:
        print("============================================")
        print("  Friction head loss calculator")
        print("  (Darcy-Weisbach, Blasius / Haaland)")
        print("============================================")
        print("  At any prompt:")
        print("    - 'm', 'menu', 'main'   -> go back to main menu")
        print("    - 'q', 'quit', 'exit'   -> quit\n")

    rho = RHO_WATER_20C
    mu = MU_WATER_20C
    g = G_DEFAULT

    while True:
        try:
            geom_opt = _select_geometry_option()
            if geom_opt == "3":
                if LANG == "es":
                    print("Saliendo... ¡hasta luego!")
                else:
                    print("Quitting... goodbye!")
                break

            # 1) D y v -> Q / D and v -> Q
            ref_diameter_m, ref_velocity_ms, q_m3s = _ask_reference_diameter_and_velocity()

            # 2) Calcular Re estimado y mostrar régimen / compute Re and show regime
            Re_ref = compute_reynolds(
                velocity_ms=ref_velocity_ms,
                diameter_m=ref_diameter_m,
                rho=rho,
                mu=mu,
            )
            regime_ref_raw = classify_regime(Re_ref)
            regime_ref = _localize_regime(regime_ref_raw)
            if LANG == "es":
                print(f"Re estimado con D_ref y v_ref: Re = {Re_ref:.3e} ({regime_ref})")
            else:
                print(f"Estimated Re with D_ref and v_ref: Re = {Re_ref:.3e} ({regime_ref})")

            # 3) Elegir método en base a ese Re / choose method based on Re
            method = _select_correlation_method(Re_ref)

            # 4) Resolver problema geométrico / solve geometric problem
            if geom_opt == "1":
                if LANG == "es":
                    print("Se usará el diámetro de referencia para el tramo (puede modificarlo si desea).\n")
                else:
                    print("The reference diameter will be used for the segment (you can modify it if needed).\n")
                seg = _ask_pipe_segment(1, default_diameter_m=ref_diameter_m)
                _print_single_result(q_m3s, seg, method, rho, mu, g)
            elif geom_opt == "2":
                _handle_pipe_with_elbow_case(q_m3s, ref_diameter_m, method, rho, mu, g)

        except GoToMainMenu:
            if LANG == "es":
                print("\nVolviendo al menú principal...\n")
            else:
                print("\nGoing back to main menu...\n")
            continue
        except QuitProgram:
            if LANG == "es":
                print("\nSaliendo... ¡hasta luego!")
            else:
                print("\nQuitting... goodbye!")
            break


if __name__ == "__main__":
    main()
