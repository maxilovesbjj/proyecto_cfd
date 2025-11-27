import argparse
import json
import sys
from typing import Any

from .calculator import (
    GeometryInput,
    compute_mesh_recommendations,
    MeshRecommendations,
)


def _fmt_float(x: float) -> str:
    """Formatea flotantes de forma compacta."""
    return f"{x:.6g}"


def print_human_readable(rec: MeshRecommendations) -> None:
    g = rec.geometry
    print("=" * 72)
    print(" Calculadora de parámetros de mallado para Salome/NETGEN")
    print(" (backend salome_mesh_generator)")
    print("=" * 72)
    print()
    print("Entrada geométrica:")
    print(f"  D           = {g.D} [m]")
    print(f"  L_in        = {g.L_in} [m]")
    print(f"  L_out       = {g.L_out} [m]")
    print(f"  R           = {g.R} [m]")
    print(f"  theta       = {g.theta_deg} [°]")
    print(f"  nivel       = {rec.level}")
    print()

    print("NETGEN 3D Parameters (global):")
    print(f"  Max Size    = { _fmt_float(rec.netgen_3d.max_size) }  [m]")
    print(f"  Min Size    = { _fmt_float(rec.netgen_3d.min_size) }  [m]")
    print(f"  Growth rate = { _fmt_float(rec.netgen_3d.growth_rate) }")
    print()

    # Recomendación de algoritmos y opciones de la pestaña Arguments
    args = rec.netgen_arguments
    print("Recomendación de algoritmos en Salome:")
    print(f"  Algoritmo 3D principal recomendado : {args.main_3d_algorithm}")
    print("    (1D, 2D y 3D en el mismo NETGEN: cómodo para el codo)")
    print()
    print("  Alternativa (si prefieres separar):")
    print(f"    3D : {args.alternative_3d_algorithm}")
    print(f"    2D : {args.alternative_2d_algorithm}")
    print(f"    1D : {args.alternative_1d_algorithm}")
    print()
    print("  En la pestaña 'Arguments' de NETGEN:")
    print("    Fineness                  = Custom")
    print(f"    Nb. Segs per Edge         = {args.nb_segs_per_edge}")
    print(f"    Nb. Segs per Radius       = {args.nb_segs_per_radius}")
    print(f"    Chordal Error             = { _fmt_float(args.chordal_error) }  [m]")
    print(
        f"    Limit Size by Surface Curvature = "
        f"{'ON  (marcado)' if args.limit_size_by_curvature else 'OFF (desmarcado, recomendado)'}"
    )
    print(
        f"    Quad-dominated            = "
        f"{'ON  (cuads donde se pueda)' if args.quad_dominated else 'OFF (triángulos, recomendado)'}"
    )
    print(
        f"    Second Order              = "
        f"{'ON  (2º orden)' if args.second_order else 'OFF (1er orden, recomendado para OpenFOAM)'}"
    )
    print(
        f"    Optimize                  = "
        f"{'ON  (mejor calidad, algo más lento)' if args.optimize else 'OFF'}"
    )
    print()

    print("Local Sizes sugeridos:")
    print("  Tamaños base:")
    print(f"    s_bulk          = { _fmt_float(rec.local_sizes.s_bulk) }  [m]  (≈ D / N_bulk)")
    print(f"    s_elbow         = { _fmt_float(rec.local_sizes.s_elbow) }  [m]  (≈ D / (2·N_bulk))")
    print(f"    s_theta         = { _fmt_float(rec.local_sizes.s_theta) }  [m]  (circunferencia)")
    print()
    print("  Para aplicar en Salome (pestaña 'Local Sizes'):")
    print(f"    * En el grupo de caras del codo (p.ej. 'elbow_wall'):")
    print(f"        On Faces → Size = { _fmt_float(rec.local_sizes.s_wall_elbow) }  [m]")
    print(f"    * (Opcional) En los tramos rectos:")
    print(f"        On Faces → Size = { _fmt_float(rec.local_sizes.s_wall_straight) }  [m]")
    print()

    print("Hipótesis 1D (Number of Segments):")
    print(f"  Entrada (N_in):")
    print(f"    calculado   = {rec.segments_1d.N_in_raw}")
    print(f"    usado       = {rec.segments_1d.N_in}")
    print()
    print(f"  Salida (N_out):")
    print(f"    calculado   = {rec.segments_1d.N_out_raw}")
    print(f"    usado       = {rec.segments_1d.N_out}")
    print()
    print(f"  Arco codo (N_arc):")
    print(f"    calculado   = {rec.segments_1d.N_arc_raw}")
    print(f"    usado       = {rec.segments_1d.N_arc}")
    print()

    print("Viscous Layers (para hipótesis 'Viscous Layers' en NETGEN 3D):")
    print(f"  Total thickness  = { _fmt_float(rec.viscous_layers.total_thickness) }  [m]")
    print(f"  Number of layers = {rec.viscous_layers.number_of_layers}")
    print(f"  Stretch factor   = { _fmt_float(rec.viscous_layers.stretch_factor) }")
    print()

    if rec.notes:
        print("Notas:")
        for note in rec.notes:
            print(f"  - {note}")
        print()


# ===========================
#  MODO INTERACTIVO
# ===========================

def ask_float(
    prompt: str,
    default: float | None = None,
    min_value: float | None = None,
    allow_zero: bool = True,
) -> float:
    """
    Pregunta por un número en consola, con validación básica.
    Si el usuario aprieta ENTER y hay default, se usa ese valor.
    """
    while True:
        if default is not None:
            txt = input(f"{prompt} [ENTER = {default:.6g}]: ")
        else:
            txt = input(f"{prompt}: ")

        txt = txt.strip()

        if not txt:
            if default is not None:
                return float(default)
            print("  Por favor escribe un número (o Ctrl+C para salir).")
            continue

        try:
            val = float(txt)
        except ValueError:
            print("  No entendí ese número, intenta de nuevo.")
            continue

        if min_value is not None:
            if allow_zero:
                if val < min_value:
                    print(f"  El valor debe ser ≥ {min_value}. Intenta de nuevo.")
                    continue
            else:
                if val <= min_value:
                    print(f"  El valor debe ser > {min_value}. Intenta de nuevo.")
                    continue

        return val


def choose_level(default: str = "medium") -> str:
    """
    Pregunta el nivel de malla de forma explicativa.
    """
    print()
    print("Nivel de malla (control de resolución):")
    print("  1) coarse  - malla más gruesa, menos celdas (rápida, menos detalle)")
    print("  2) medium  - compromiso recomendado (buena primera simulación)")
    print("  3) fine    - malla más fina, más celdas (más precisa, más lenta)")
    print()

    default_label = default
    while True:
        choice = input(
            f"Elige nivel [1/2/3 o coarse/medium/fine] "
            f"[ENTER = {default_label}]: "
        ).strip().lower()

        if not choice:
            return default

        if choice in ("1", "coarse", "c"):
            return "coarse"
        if choice in ("2", "medium", "m"):
            return "medium"
        if choice in ("3", "fine", "f"):
            return "fine"

        print("  No entendí la elección. Escribe 1, 2, 3 o coarse/medium/fine.")


def run_interactive() -> None:
    """
    Asistente interactivo: te pregunta todos los datos de entrada
    y luego imprime el resumen de parámetros para Salome/NETGEN.
    """
    print("=" * 72)
    print(" Asistente de configuración de mallado para Salome/NETGEN")
    print("=" * 72)
    print()
    print("Te voy a pedir algunos datos de la geometría del codo:")
    print("  - D: diámetro interno de la tubería [m]")
    print("  - L_in: largo recto de ENTRADA [m]")
    print("  - L_out: largo recto de SALIDA [m]")
    print("  - R: radio del codo [m]")
    print("  - theta: ángulo del codo [grados] (p.ej. 45, 90)")
    print("  - nivel de malla: coarse / medium / fine")
    print()
    print("Con eso se van a calcular:")
    print("  - Max/Min Size y growth rate de NETGEN 3D")
    print("  - Local Sizes (refinando el codo en 'elbow_wall')")
    print("  - Nº de segmentos en entrada, salida y arco del codo")
    print("  - Parámetros de 'Viscous Layers'")
    print("  - Sugerencia de algoritmos y checkboxes de NETGEN")
    print()

    # 1) Diámetro D
    print("Primero, el diámetro interno D.")
    print("Ejemplos:")
    print("  - 0.05  → 5 cm")
    print("  - 0.10  → 10 cm")
    print("  - 0.25  → 25 cm")
    print()
    D = ask_float(
        "Diámetro interno D [m] (debe ser > 0)",
        default=None,
        min_value=0.0,
        allow_zero=False,
    )

    # Con D ya podemos sugerir valores típicos:
    default_L_in = 20.0 * D
    default_L_out = 20.0 * D
    default_R = 1.5 * D
    default_theta = 90.0

    # 2) L_in
    print()
    print("Ahora los largos rectos de ENTRADA y SALIDA.")
    print("Es típico usar ~20·D de entrada y ~20·D de salida.")
    print(f"Con D = {D:.6g} m, 20·D ≈ {default_L_in:.6g} m.")
    print()
    L_in = ask_float(
        "Largo recto de ENTRADA L_in [m]",
        default=default_L_in,
        min_value=0.0,
        allow_zero=True,
    )

    # 3) L_out
    L_out = ask_float(
        "Largo recto de SALIDA L_out [m]",
        default=default_L_out,
        min_value=0.0,
        allow_zero=True,
    )

    # 4) R
    print()
    print("Radio del codo R:")
    print("  - Codo de radio corto  (SR) ≈ 1·D")
    print("  - Codo de radio largo  (LR) ≈ 1.5·D")
    print(f"Con D = {D:.6g} m, 1.5·D ≈ {default_R:.6g} m.")
    print()
    R = ask_float(
        "Radio del codo R [m]",
        default=default_R,
        min_value=0.0,
        allow_zero=False,
    )

    # 5) theta
    print()
    print("Ángulo del codo theta:")
    print("  - 45  → codo de 45°")
    print("  - 90  → codo de 90° (típico)")
    print()
    theta = ask_float(
        "Ángulo del codo theta [grados]",
        default=default_theta,
        min_value=0.0,
        allow_zero=False,
    )

    # 6) nivel
    level = choose_level(default="medium")

    # Construir geometría y calcular
    geom = GeometryInput(
        D=D,
        L_in=L_in,
        L_out=L_out,
        R=R,
        theta_deg=theta,
        level=level,
    )

    try:
        rec = compute_mesh_recommendations(geom)
    except ValueError as e:
        print()
        print(f"[ERROR] {e}")
        sys.exit(1)

    print()
    print_human_readable(rec)


# ===========================
#  MODO NO INTERACTIVO (CLI)
# ===========================

def parse_args(argv: Any = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generador de parámetros de mallado para Salome/NETGEN "
            "en función de D, geometría del codo y nivel de malla."
        )
    )
    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="Modo asistente interactivo (te va preguntando paso a paso).",
    )
    parser.add_argument("--D", type=float,
                        help="Diámetro interno [m].")
    parser.add_argument("--L-in", dest="L_in", type=float,
                        help="Largo recto de entrada [m].")
    parser.add_argument("--L-out", dest="L_out", type=float,
                        help="Largo recto de salida [m].")
    parser.add_argument("--R", type=float,
                        help="Radio del codo [m].")
    parser.add_argument("--theta", type=float,
                        help="Ángulo del codo [grados].")
    parser.add_argument(
        "--level", "-l",
        type=str,
        default="medium",
        help="Nivel de malla: coarse / medium / fine (por defecto: medium)."
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Imprime la salida en formato JSON (útil para integrarlo con otras tools).",
    )
    return parser.parse_args(argv)


def main(argv: Any = None) -> None:
    args = parse_args(argv)

    # Si está en modo interactivo, o no se ha pasado ningún parámetro geométrico,
    # lanzamos el asistente interactivo.
    if args.interactive or all(
        getattr(args, name) is None
        for name in ("D", "L_in", "L_out", "R", "theta")
    ):
        run_interactive()
        return

    missing = [
        name for name in ("D", "L_in", "L_out", "R", "theta")
        if getattr(args, name) is None
    ]
    if missing:
        print(
            "Faltan argumentos: "
            + ", ".join(missing)
            + ". Usa --interactive para modo asistente.",
            file=sys.stderr,
        )
        sys.exit(1)

    geom = GeometryInput(
        D=args.D,
        L_in=args.L_in,
        L_out=args.L_out,
        R=args.R,
        theta_deg=args.theta,
        level=args.level,
    )

    try:
        rec = compute_mesh_recommendations(geom)
    except ValueError as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)

    if args.json:
        d = rec.to_dict()
        print(json.dumps(d, indent=2, sort_keys=False))
    else:
        print_human_readable(rec)


if __name__ == "__main__":
    main()
