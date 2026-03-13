"""Compatibilidad de namespace contractual: maroc_b2b.api.gerencial.*"""

from gcma_kiosco.api.gerencial import (
    export_scorecard_csv,
    get_cobertura_mapa,
    get_panel_gerencial_360,
    get_reporte_fotos_competencia,
    run_alerta_abandono_clientes,
)

__all__ = [
    "get_panel_gerencial_360",
    "get_cobertura_mapa",
    "get_reporte_fotos_competencia",
    "run_alerta_abandono_clientes",
    "export_scorecard_csv",
]
