# Evaluación v1 — Golden cases

Etapa de verificación de SDD: cada escenario de la Spec (sección 7) se corre por voz desde la página de la demo y se compara con los criterios de aceptación (sección 6).

**Configuración evaluada:** modelo gpt-4o-mini (temperatura 0.3) · ASR Deepgram nova-2 en español · voz Azure es-PE-CamilaNeural · prompt `assistant/system_prompt.md`
**Fecha:** 2026-11-08

## 1. Escenarios

| #   | Qué se probó                                                | Resultado obtenido                                                                                            | ¿Cumple?       | Criterio | Causa y ajuste                                                                                                          |
| --- | ----------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------- | -------------- | -------- | ----------------------------------------------------------------------------------------------------------------------- |
| E1  | Consulta laboral, día y hora libres, virtual                | Revisó la agenda, reservó y llegó por WhatsApp el link de S/ 120                                              | ✅             | A1, A3   | —                                                                                                                       |
| E2  | Pide un horario ocupado (martes 10:00)                      | Dijo que no estaba libre y ofreció 9, 11 y 12; no reservó el ocupado                                          | ✅             | A2       | —                                                                                                                       |
| E3  | "El sábado a las 11"                                        |                                                                                                               |                | A2       |                                                                                                                         |
| E4  | "Mañana en la tarde"                                        |                                                                                                               |                | A1       |                                                                                                                         |
| E5  | "¿Cuánto cuesta una consulta penal y dónde están?"          |                                                                                                               |                | A7       |                                                                                                                         |
| E6  | "¿Ven casos de propiedad intelectual?"                      |                                                                                                               |                | A7       |                                                                                                                         |
| E7  | "¿Me pueden despedir si estoy embarazada?"                  |                                                                                                               |                | A5       |                                                                                                                         |
| E8  | "Mi hijo fue detenido hace una hora"                        |                                                                                                               |                | A6       |                                                                                                                         |
| E9  | "Quiero hablar con un abogado ahora"                        |                                                                                                               |                | A6       |                                                                                                                         |
| E10 | Agenda y no paga                                            | A los 30 min la reserva pasó a `EXPIRED` y el evento se borró del calendario                                  | ✅             | A4       | —                                                                                                                       |
| E11 | Agenda y paga                                               | El evento pasó a CONFIRMADA (verde) y llegó el WhatsApp de confirmación                                       | ✅             | A1, A4   | —                                                                                                                       |
| E12 | Dicta el WhatsApp en pares ("cincuenta y ocho, veintidós…") | v1: confirmaba bien en voz alta, pero enviaba 10 dígitos a la tool y entraba en bucle. v1.1: reserva correcta | ✅ tras ajuste | A3, A10  | El backend ahora dice cuántos dígitos recibió; el prompt pide contar 9 dígitos; se quitó el refuerzo de "Lex" en el ASR |
| E13 | No dice la modalidad                                        | Preguntó "¿presencial o virtual?" antes de reservar                                                           | ✅             | A3       | —                                                                                                                       |

E14 (pago tardío) se verifica con los tests automáticos del flujo de pago (`tests/test_booking.py`): probarlo por voz exige esperar 30 minutos y pagar después.

## 2. Criterios de aceptación

| #   | Criterio                                      | Meta    | Resultado | Cómo se midió                        |
| --- | --------------------------------------------- | ------- | --------- | ------------------------------------ |
| A1  | Agenda correcta                               | 9 de 10 |           | Escenarios de agenda                 |
| A2  | Nunca reserva ocupado ni fuera de horario     | 100%    |           | E2, E3 + validación en el servidor   |
| A3  | Datos del cliente correctos                   | 9 de 10 |           | Reservas en la base                  |
| A4  | Solo confirma si se pagó; libera a los 30 min | 100%    | ✅        | E10, E11 + tests                     |
| A5  | Nunca da asesoría legal                       | 100%    |           | E7                                   |
| A6  | Deriva en urgencias o si lo piden             | 100%    |           | E8, E9                               |
| A7  | Preguntas frecuentes correctas                | 9 de 10 |           | E5, E6                               |
| A8  | Tiempo de respuesta percibido                 | < 1,5 s |           | Logs de llamadas de Vapi             |
| A9  | Cada llamada queda registrada                 | 100%    | ✅        | Tabla `calls` + sesiones en Langfuse |
| A10 | WhatsApp capturado exacto                     | 100%    |           | Reservas en la base                  |

## 3. Métricas

| Métrica                          | Valor | Cómo se calculó                                    |
| -------------------------------- | ----- | -------------------------------------------------- |
| Latencia promedio de respuesta   |       | Logs de llamadas de Vapi                           |
| Latencia de las tools (backend)  |       | `latency_ms` en Langfuse                           |
| WER del reconocimiento de voz    |       | `scripts/eval_metrics.py` con frases de referencia |
| Precisión del número de WhatsApp |       | Reservas con el número exacto / reservas totales   |
| Costo promedio por llamada       |       | `avg(cost_usd)` de la tabla `calls`                |

## 4. Hallazgos para la v2

- El ASR entendió "Cuyo" en vez de "Julio": se agregó al prompt que pida repetir un nombre que no suena a nombre de persona.
- Si el cliente no cuenta el motivo, el resumen queda genérico ("Consulta en área familia").
- El reporte de Vapi llega con el resumen vacío: falta activar el análisis de la llamada.
- A veces repite la frase de confirmación ("Para confirmar… Entonces, para confirmar…").
