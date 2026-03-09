"""
Utilidades de parsing para códigos QR de la fábrica GCMA.

FORMATO QR ESTÁNDAR (contrato entre etiqueta Zebra y API Kiosco):
    <item_code>|<batch_no>

Ejemplos:
    MP-RES-ALK-G70|LOTE-RES-2026-0001
    PT-PIN-BLC-MAT-20L|LOT-PIN-2026-0150

Este módulo centraliza el parsing para que si el formato del QR
cambia en el futuro (ej. se añade un tercer campo), solo hay que
tocar UN archivo.
"""

# ── Separador del contenido QR (compartido con el diseño de etiqueta Zebra) ──
QR_SEPARATOR = "|"


def parse_qr_material(qr_data: str) -> tuple:
    """Parsea el contenido de un QR de material/lote.

    Args:
        qr_data: String leído por el escáner (ej. "MP-RES-ALK-G70|LOTE-RES-2026-0001")

    Returns:
        (item_code, batch_no) si el formato es válido.
        (None, None) si el QR no es parseable.
    """
    if not qr_data or not isinstance(qr_data, str):
        return None, None

    qr_data = qr_data.strip()
    parts = qr_data.split(QR_SEPARATOR)

    if len(parts) != 2:
        return None, None

    item_code = parts[0].strip()
    batch_no = parts[1].strip()

    if not item_code or not batch_no:
        return None, None

    return item_code, batch_no


def build_qr_material(item_code: str, batch_no: str) -> str:
    """Genera el contenido QR para una etiqueta Zebra.

    Usado por el Print Format de etiquetas para generar el texto
    que se codificará en el QR impreso.

    Args:
        item_code: Código interno del item (ej. "MP-RES-ALK-G70")
        batch_no: Número de lote (ej. "LOTE-RES-2026-0001")

    Returns:
        String formateado para codificar en QR.
    """
    return f"{item_code}{QR_SEPARATOR}{batch_no}"
