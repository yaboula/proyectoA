# Base de Datos y DocTypes: Bloque 3 Comercial y Logística (Frappe)

*Documento Arquitectónico para Desarrolladores Backend / AI Agents.*
*Objetivo: Cero ambigüedad en la creación de campos y DocTypes.*

## 1. Modificaciones a DocTypes Nativos (Custom Fields)

Para mantener la base Core de ERPNext limpia pero adaptada a Marruecos, crearemos **Custom Fields** mediante Fixtures en la App personalizada.

### DocType: `Customer` (Droguería / B2B)
Nuevos campos a añadir vía "Customize Form":
*   `gps_lat` (Data): Latitud oficial de la droguería (Geo-fence center).
*   `gps_lng` (Data): Longitud oficial de la droguería.
*   `tipo_drogueria` (Select): Valores: [Mayorista, Minorista, Distribuidor Regional].
*   `foto_fachada` (Attach Image): Identificación visual para comerciales nuevos.
*   `id_comercial_asignado` (Link -> Sales Person): Usuario Frappe dueño de la cuenta.

### DocType: `Item` (Catálogo Químico/Pintura)
*   `es_promocionable_fefo` (Check): Indica si el Portal B2B puede hacer autodescuento cuando quede poco para vencer.
*   `puntos_fidelidad_base` (Int): Puntos que gana el cliente por cada unidad comprada.

### DocType: `Delivery Note` (Albarán / Expedición)
*   `firma_receptor` (Attach Image): Lienzo Base64 enviado por el Chofer PWA.
*   `foto_sello_pod` (Attach Image): Foto del sello húmedo de la droguería.
*   `estado_entrega_pwa` (Select): Valores: [En Tránsito, Entregado, Rechazado Parcial, Rechazado Total].
*   `gps_entrega_lat`, `gps_entrega_lng` (Data): Auditoría del Chofer.

---

## 2. Nuevos DocTypes Propios (Custom App)

Crear estos DocTypes con `Is Submittable = 1` si implican transacción (ej: Pedidos B2B) o `0` si son catálogos. Prefijo recomendado en BD: `tab` (Nativo) pero la App se llamará `maroc_b2b`.

### DocType: `Ruta_Comercial_Dia` (Transaccional)
*Control de la Hoja de Ruta diaria del Visitador.*
*   `comercial` (Link -> Sales Person)
*   `fecha_ruta` (Date)
*   `estado` (Select): [Planificada, En Curso, Completada]
*   **Tabla Hija:** `Visitas_Programadas` (Link -> Customer, Orden_Visita (Int))

### DocType: `CheckIn_Visita` (Transaccional - Creado 100% por PWA)
*Auditoría de presencia física del vendedor en la droguería.*
*   `cliente` (Link -> Customer)
*   `comercial` (Link -> User)
*   `timestamp_in` (Datetime)
*   `timestamp_out` (Datetime)
*   `gps_lat_capturada` (Data)
*   `gps_lng_capturada` (Data)
*   `es_visita_valida` (Check): Calculado en Backend. Distancia Euclidiana(gps_capturada, gps_cliente) < 500m.
*   `motivo_no_venta` (Select): [Stock Alto, Sin Dinero, Dueño Ausente, Prefiere Competencia]. Solo requerido si la visita no germinó un Pedido (Sales Order).

### DocType: `Sync_Error_Log` (Log del Sistema)
*Manejo de errores del ServiceWorker/IndexedDB del PWA Offline.*
*   `payload_json` (Text)
*   `usuario` (Link -> User)
*   `endpoint_destino` (Data)
*   `mensaje_error_backend` (Data)

---

## 3. Roles y Permisos (Frappe Role Profile)

Crear estrictamente estos **Role Profiles** para asignar fácilmente en campo:
1.  **Vendedor_Calle_B2B**: 
    *   Lee: `Item`, `Customer` (Solo los suyos), `Sales Order` (Solo suyas).
    *   Crea: `Sales Order` (Draft), `CheckIn_Visita`.
    *   NO puede hacer Submit automático si el Límite de Crédito del cliente en `Customer` excede la regla.
2.  **Operario_Tablet_FEFO**:
    *   Lee: `Sales Order` (Submitidas), `Bin` (Stock).
    *   Crea/Emite: `Delivery Note` (Draft a Submit).
3.  **Chofer_Reparto_POD**:
    *   Lee: `Delivery Note` (En Tránsito).
    *   Modifica: Puede adjuntar Firma/Foto a `Delivery Note`.
4.  **Drogueria_Portal_B2B**: 
    *   Rol de Frappe Portal restringido. Solo ve DocTypes vinculados a su ID de Cliente.

---

## Reglas para el Backend Dev (Agent)
1. **Nunca** crear scripts en el JS del Front-End que calculen el límite de Deuda y bloqueen al vendedor. Todo cálculo financiero (Estado de cuenta) **DEBE VIVIR** en un `frappe.whitelist()` de lectura rápida en el Backend.
2. Toda tabla hija en PWA (carrito de pedido offline) debe mapear sus nombres de columnas *exactamente* a los `fieldname` definidos aquí, para que el ORM de Frappe inserte el JSON del ServiceWorker sin necesidad de parseadores manuales en Python.
