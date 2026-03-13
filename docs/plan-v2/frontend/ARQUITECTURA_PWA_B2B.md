# Arquitectura Frontend PWA (Bloque 3 - Comercial B2B)

*Documento Arquitectónico para Desarrolladores Frontend (Vue / PWA).*
*Objetivo: Cero pérdidas de pedidos por falta de red 4G en zonas rurales de Marruecos.*

## 1. Patrón Offline-First (Sync Queue)

La aplicación del Comercial (App Rutas/Pedidos) debe operar bajo la premisa de que "Internet no existe" hasta que se pruebe lo contrario.

### 1.1 Estructura de `IndexedDB` (idb)
Debes implementar `idb` (o dexie.js) con al menos las siguientes "tablas" (Object Stores):
*   `store_catalogo`: Copia local (cacheada 1 vez al día) de los Items (Nombre, Precio Base, Stock Proyectado en fecha de cacheo).
*   `store_clientes`: Copia local de los clientes de la ruta del comercial (ID, Nombre, Saldo Vencido pre-cargado a las 8 AM).
*   `sync_outbox`: **La cola sagrada.** Todo `POST` (CheckIn GPS, Pedido B2B Nuevo, Cobro Recibido) *SIEMPRE* se escribe primero aquí.

### 1.2 Flujo del ServiceWorker (Background Sync)
Al hacer click en "Registrar Check-In" o "Enviar Pedido":
1. El UI Component hace un save al `sync_outbox` de `IndexedDB`.
2. El UI asume estado "Guardado" (Iconito de nube con flecha gris en la tarjeta del pedido).
3. El componente notifica al ServiceWorker (mediante `navigator.serviceWorker.ready`).
4. El SW lee la red `navigator.onLine`.
   * **Si hay red:** Saca el registro del outbox, llama a la API `/api/comercial/sync_pedidos_offline`.
   * **Si no hay red:** Guarda el evento en el Workbox BackgroundSync Queue. Tan pronto como el celular tome cobertura (así esté en el bolsillo del comercial), el SW lanza la petición en background.

---

## 2. Requerimientos de UI/UX "Fat-Finger"

*   **Toques Grandes:** Botones de Check-In y "+ Añadir al Carrito" de mínimo `48px` x `48px` (Estándar iOS Human Interface en un país donde se usan guantes o manos muy grandes/manchadas de pintura).
*   **Feedback Háptico:** Usar el API nativa de vibración `navigator.vibrate(200)` cuando:
    * Se escanea correctamente un Código de Barras / QR en el kiosco FEFO.
    * Se finaliza con éxito una "Toma de Pedido" en modo Offline.
*   **Captura de Imágenes Nativas:** Para la aplicación del Chofer (POD), usar el atributo HTML5 estricto para forzar la cámara trasera y evitar que escojan de la galería:
    ```html
    <input type="file" accept="image/jpeg, image/png" capture="environment">
    ```

---

## 3. Seguridad Angular/Vue
*   El JWT o Session Cookie no se almacena jamás en localStorage sin expiración.
*   Si el PWA detecta un Token caducado pero tiene elementos en la `sync_outbox`, detiene la sincronización y lanza una **Alerta Persistente Red** al vendedor: "Inicia Sesión urgente para subir XX pedidos almacenados".
