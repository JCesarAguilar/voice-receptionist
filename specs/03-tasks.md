# Tasks v1 — Recepcionista de voz

Etapa 3 de SDD: 23 tareas de 1 a 3 horas, en orden. Cada una tiene un criterio de "hecho" verificable; no se pasa a la siguiente sin cumplirlo. Las fases 0 y 1 no necesitan cuentas externas ni gastan dinero.

## Fase 0 — Setup

- [x] **T01 · Repo y estructura.** Crear el repo `voice-receptionist`, el `.venv`, las carpetas del Plan, `requirements.txt` con versiones fijas, `.gitignore`, `.env.example` y copiar la Spec, el Plan y estas tareas a `specs/`. _Hecho cuando:_ `uvicorn app.main:app` levanta y `GET /health` responde `{"status": "ok"}`; primer commit subido.
- [x] **T02 · Configuración.** `app/config.py` con pydantic-settings: claves, zona horaria (America/Lima) y reglas de negocio configurables. _Hecho cuando:_ si falta una clave obligatoria, la app no arranca y el error dice cuál falta; un test lo verifica.

## Fase 1 — Dominio, reglas y servicios (con fakes)

Todo se prueba sin internet: los servicios externos se reemplazan por fakes en memoria.

- [ ] **T03 · Modelos del dominio.** `domain/models.py`: `Area`, `Modality`, `BookingStatus`, `Client`, `Booking`, y la tabla de precios por área. _Hecho cuando:_ tests verifican el precio de cada área y que un número sin formato +51 se rechaza.
- [ ] **T04 · Reglas de horario.** `domain/rules.py`: horario de atención, duración de 45 + 15 min, anticipación mínima de 2 h y máxima de 30 días, y generación de horarios posibles de un día. _Hecho cuando:_ tests cubren sábado (cerrado), un horario dentro de 1 h (rechazado) y un día normal (lista correcta de horarios).
- [ ] **T05 · Puertos.** `domain/ports.py` con `CalendarPort`, `PaymentPort`, `MessagingPort` y `BookingRepository` como `Protocol`. _Hecho cuando:_ existen fakes en `tests/fakes.py` que los implementan y el verificador de tipos no marca errores.
- [ ] **T06 · Servicio de disponibilidad.** `services/availability.py`: cruza los horarios posibles con los ocupados del calendario y devuelve hasta 3, empezando por el más cercano al pedido. _Hecho cuando:_ tests reproducen E2 (ocupado → alternativas) y E3 (sábado → propone lunes).
- [ ] **T07 · Servicio de reservas.** `services/booking.py`: crear (revalida el horario, evento PENDIENTE, orden, WhatsApp), confirmar (idempotente) y expirar. _Hecho cuando:_ tests cubren E10 (expira a los 30 min), E11 (confirma y envía WhatsApp), doble confirmación (un solo WhatsApp) y horario tomado entre consulta y reserva (rechaza).
- [ ] **T08 · Servicio de derivación.** `services/handoff.py`: arma el mensaje con nombre, número, área, motivo y resumen y lo envía al responsable. _Hecho cuando:_ un test verifica el texto exacto que recibe el fake de mensajería.

## Fase 2 — Adaptadores reales

Aquí se crean las cuentas de prueba. Cada adaptador implementa su puerto; los servicios no cambian.

- [ ] **T09 · Base de datos.** `adapters/sql_repository.py` con SQLModel y SQLite. _Hecho cuando:_ un test de integración guarda una reserva, la lee y cambia su estado.
- [ ] **T10 · Google Calendar.** Cuenta de servicio con acceso al calendario del estudio; `adapters/google_calendar.py` consulta ocupados, crea, actualiza y borra eventos. _Hecho cuando:_ un script crea un evento PENDIENTE, lo pasa a CONFIRMADA y lo borra, y se ve en el calendario.
- [ ] **T11 · WhatsApp.** Twilio WhatsApp Sandbox; `adapters/twilio_whatsapp.py`. _Hecho cuando:_ un script envía un mensaje de prueba a tu WhatsApp.
- [ ] **T12 · Culqi.** Cuenta en modo integración; `adapters/culqi.py` crea y consulta órdenes. _Hecho cuando:_ un script crea una orden de S/ 120 y la consulta por su id.

## Fase 3 — API, pagos y webhooks

- [ ] **T13 · Endpoint de tools.** `schemas/tools.py` con los 3 contratos y `api/vapi_tools.py` con el dispatcher y el secreto en el encabezado. _Hecho cuando:_ tests con `TestClient` envían un payload con el formato de Vapi y reciben `results` con el `toolCallId` correcto; sin secreto, 401; con argumentos inválidos, `error` legible.
- [ ] **T14 · Página de pago.** `GET /pagar/{booking_id}` con `templates/pagar.html` y Culqi Checkout; `POST /payments/charge` para tarjeta. _Hecho cuando:_ pagas con una tarjeta de prueba de Culqi desde el navegador y la reserva queda `CONFIRMED`.
- [ ] **T15 · Webhook de Culqi.** `POST /webhooks/culqi`: verifica la orden en la API y confirma de forma idempotente. _Hecho cuando:_ un pago con Yape de prueba confirma la reserva y repetir el aviso no envía un segundo WhatsApp.
- [ ] **T16 · Expiración automática.** `jobs/expire_holds.py` con APScheduler cada minuto. _Hecho cuando:_ una reserva sin pagar pasa a `EXPIRED`, su evento desaparece del calendario y el cliente recibe el aviso.
- [ ] **T17 · ngrok.** URL pública hacia el backend local para Vapi y Culqi. _Hecho cuando:_ `GET https://<tu-url>/health` responde desde fuera.

## Fase 4 — Agente de voz

- [ ] **T18 · Prompt e información del estudio.** `assistant/estudio.md` (áreas, precios, dirección, horarios, modalidades) y `assistant/system_prompt.md` con rol, contexto, tarea, formato y los límites de la Spec. _Hecho cuando:_ el prompt cubre cada regla de la sección 5 de la Spec y está versionado.
- [ ] **T19 · Asistente en Vapi.** Modelo mini, voz en español, reconocimiento de voz en español y las 3 tools apuntando a la URL de ngrok; guardar la configuración en `assistant/tools.json`. _Hecho cuando:_ desde el panel de Vapi, una llamada de prueba agenda E1 de punta a punta.
- [ ] **T20 · Página de la demo.** Página con el Web SDK de Vapi y un botón "Hablar con la recepcionista". _Hecho cuando:_ desde el navegador se completa E1 y llega el WhatsApp con el link.
- [ ] **T21 · Observabilidad.** Traza de Langfuse por llamada con un span por tool, y webhook `end-of-call-report` guardado en la base. _Hecho cuando:_ en Langfuse se ve una llamada con sus tools, latencias y resultado.

## Fase 5 — Evaluación y entrega

- [ ] **T22 · Golden cases.** Correr E1–E13 por voz y registrar el resultado de cada uno en `specs/evaluacion.md` contra A1–A9, con la latencia promedio. _Hecho cuando:_ la tabla está completa y cada criterio fallido tiene una causa anotada.
- [ ] **T23 · Iterar y entregar.** Ajustar el prompt o las tools hasta cumplir A1–A9; README con diagrama, decisiones, setup, resultados y limitaciones; video de 1 minuto de una llamada real. _Hecho cuando:_ todos los criterios están en verde, el repo es público y el video está en el README.

Opcional después de la v1: desplegar el backend en Render o Railway, recordatorios 24 h antes, reprogramar y cancelar por voz, y pasar a la API oficial de WhatsApp.
