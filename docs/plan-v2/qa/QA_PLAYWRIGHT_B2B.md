# Plan de Pruebas E2E (Playwright) - Bloque 3 B2B

*Documento Arquitectónico para Desarrolladores de QA y SDETs.*
*Objetivo: Automatizar el "Happy Path" comercial y forzar los "Poka-Yokes" críticos (Fraude GPS, Mora, FEFO).*

---

## 1. Suite: `comercial-rutas.spec.js` (Sub-bloque 3A)
**Pruebas obligatorias:**
1.  **Bloqueante Login Móvil:** Acceder al PWA en un viewport móvil (iPhone 13), hacer login y verificar redirección automática al *Dashboard* del Visitador.
2.  **Validación GPS Exitoso:** Interceptar el llamado del navegador a `navigator.geolocation.getCurrentPosition` en Playwright y simular las coordenadas exactas de la Droguería A. El endpoint `/api/comercial/post_checkin` debe devolver HTTP 200 y mensaje `es_fraude: false`.
3.  **Fraude de Geocerca (Poka-Yoke):** Mock de ubicación GPS enviando coordenadas de "España" para visitar una "Droguería en Casablanca". El check-in entra, pero la API debe devolver HTTP 200 con `es_fraude: true` (se registra para revisión del Gerente).

## 2. Suite: `pedidos-offline.spec.js` (Sub-bloque 3A)
**Prueba Especial: Network Interception (IndexedDB)**
1.  **Carga Base:** Login y acceso al Perfil "Droguería B". Verificación de límite de crédito OK.
2.  **Modo Offline:** Apagar la red en Playwright (`context.setOffline(true)`).
3.  **Toma de Pedido:** Añadir 5 litros de Solvent al Carrito y pulsar "Procesar".
4.  **Confirmación UI:** El UI debe mostrar Toast: *"Guardado Localmente: Sin Conexión"*. El pedido *no debe estar* en el Backend Frappe si hacemos un assert directo por API.
5.  **Reconexión:** `context.setOffline(false)`. Esperar evento de Background Sync.
6.  **Paso de Vida:** Hacer assert directo por API en Frappe comprobando que el `Sales Order` ahora sí existe.

## 3. Suite: `almacen-picking-fefo.spec.js` (Sub-bloque 3B)
**Pruebas obligatorias (Kiosco Tablet):**
1.  **Poka-Yoke FEFO Estricto:** 
    *   Precondición: Setup mediante script Python de dos lotes: LOTE-VIEJO (vence en 30 días) y LOTE-NUEVO (Vence en 60 días).
    *   Test E2E: Escanear el QR de LOTE-NUEVO para el pedido. El endpoint de validación DEBE arrojar `400 ValidationError` con un mensaje conteniendo "FEFO".
2.  **Happy Path Picking y BL:** Escanear el LOTE-VIEJO. Generar el cierre. Verificar en el Backend que el estado del Documento cambió y se generó el PDF de *Delivery Note*.

## 4. Suite: `portal-b2b.spec.js` (Sub-bloque 3C)
**Prueba de Seguridad (Tenant Isolation):**
1.  Login con las credenciales del "Dueño Droguería C".
2.  Intentar forzar una petición GET o crear un SOPORTE mediante inyección de API (Ej. ID: `Customer-D`).
3.  Backend debe rebotar con `403 Forbidden` (Asegurar permisos Frappe en el Portal Web).
