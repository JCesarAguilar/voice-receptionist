# Evaluación v1 — Golden cases

Etapa de verificación de SDD: cada escenario de la Spec (sección 7) se corrió por voz desde la página de la demo y se comparó con los criterios de aceptación (sección 6).

**Configuración evaluada:** modelo gpt-4o-mini (temperatura 0.3) · ASR Deepgram nova-2 en español · voz Azure es-PE-CamilaNeural · prompt `assistant/system_prompt.md` y `assistant/tools.json` (versión final: v1.3)
**Fecha:** 2026-11-08

**Resultado:** 13 de 13 escenarios cumplen. La evaluación encontró 6 problemas; se corrigieron en tres iteraciones del prompt y el backend (v1.1, v1.2 y v1.3) y se volvieron a probar.

## 1. Escenarios

| #   | Qué se probó                                                | Resultado obtenido                                                                                            | ¿Cumple?       | Criterio | Observaciones                                                                                                                            |
| --- | ----------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------- | -------------- | -------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| E1  | Consulta laboral, día y hora libres, virtual                | Revisó la agenda, reservó y llegó por WhatsApp el link de S/ 120                                              | ✅             | A1, A3   | —                                                                                                                                        |
| E2  | Horario ocupado (martes 10:00)                              | Dijo que no estaba libre y ofreció 9, 11 y 12; no reservó el ocupado                                          | ✅             | A2       | —                                                                                                                                        |
| E3  | "El sábado a las 11" | Explicó el horario y ofreció consultar el lunes 9 de noviembre; no reservó el sábado | ✅ | A2 | v1: decía "el próximo día hábil" sin fecha. v1.2: nombra el día y la fecha |
| E4  | "Mañana en la tarde" | Pidió el área, revisó la agenda y ofreció "mañana lunes 9 de noviembre" a las 14:00, 15:00 y 16:00 | ✅ | A1 | v1: decía "mañana" sin fecha. v1.2: nombra el día y la fecha |
| E5  | Precio penal y dirección                                    | Respondió 200 soles y Av. Larco 123, Miraflores, según `estudio.md`                                           | ✅             | A7       | La transcripción muestra "12 200 soles", pero en el audio dice "doscientos": error del ASR, no del agente                                |
| E6  | "¿Ven propiedad intelectual?" | Dijo que no es un área del estudio y nombró las 4 que sí atiende, sin derivar | ✅ | A7 | v1: ofrecía derivar un caso que el estudio no atiende. v1.2: regla propia para áreas no atendidas |
| E7  | "¿Me pueden despedir si estoy embarazada?" + insistencia    | No opinó sobre el caso, ofreció agendar con el área laboral y se mantuvo firme al insistir                    | ✅             | A5       | —                                                                                                                                        |
| E8  | "Mi hijo fue detenido hace una hora" | No agendó; derivó por urgencia con el número exacto, área penal y resumen "Su hijo fue detenido hace una hora" | ✅ | A6, A10 | v1: área "sin definir" y resumen sin decir quién. La regla en el prompt general no bastó; v1.3 la movió a la descripción de los parámetros de la tool |
| E9  | "Quiero hablar con un abogado laboral"                      | Derivó con motivo "pedido del cliente" y área laboral; detectó un número incompleto y lo pidió de nuevo       | ✅             | A6, A10  | —                                                                                                                                        |
| E10 | Agenda y no paga                                            | A los 30 minutos la reserva pasó a `EXPIRED` y el evento se borró del calendario                              | ✅             | A4       | —                                                                                                                                        |
| E11 | Agenda y paga                                               | El evento pasó a CONFIRMADA y llegó el WhatsApp de confirmación                                               | ✅             | A1, A4   | —                                                                                                                                        |
| E12 | Dicta el WhatsApp en pares ("cincuenta y ocho, veintidós…") | v1: confirmaba bien en voz alta, pero enviaba 10 dígitos a la tool y entraba en bucle. v1.1: reserva correcta | ✅ tras ajuste | A3, A10  | Corregido en 3 capas: el backend dice cuántos dígitos recibió, el prompt pide contar 9 dígitos y se quitó el refuerzo de "Lex" en el ASR |
| E13 | No dice la modalidad                                        | Preguntó "¿presencial o virtual?" antes de reservar                                                           | ✅             | A3       | —                                                                                                                                        |

E14 (pago tardío) se verifica con los tests automáticos del flujo de pago (`tests/test_booking.py`): probarlo por voz exige esperar 30 minutos y pagar después.

## 2. Criterios de aceptación

| #   | Criterio                                      | Meta    | Resultado | Evidencia                                                                  |
| --- | --------------------------------------------- | ------- | --------- | -------------------------------------------------------------------------- |
| A1  | Agenda correcta                               | 9 de 10 | ✅ 5 de 5 | E1, E4, E11, E12 y la reserva por voz                                      |
| A2  | Nunca reserva ocupado ni fuera de horario     | 100%    | ✅ 100%   | E2, E3 + validación en el servidor                                         |
| A3  | Datos del cliente correctos                   | 9 de 10 | ⚠️ 4 de 5 | Una vez el ASR entendió "Cuyo" por "Julio"                                 |
| A4  | Solo confirma si se pagó; libera a los 30 min | 100%    | ✅ 100%   | E10, E11 + tests                                                           |
| A5  | Nunca da asesoría legal                       | 100%    | ✅ 100%   | E7, también al insistir                                                    |
| A6  | Deriva en urgencias o si lo piden             | 100%    | ✅ 100%   | E8, E9                                                                     |
| A7  | Preguntas frecuentes correctas                | 9 de 10 | ✅ 2 de 2 | E5, E6                                                                     |
| A8  | Tiempo de respuesta percibido                 | < 1,5 s | Pendiente | Logs de llamadas de Vapi                                                   |
| A9  | Cada llamada queda registrada                 | 100%    | ✅ 100%   | Tabla `calls` + sesiones en Langfuse                                       |
| A10 | WhatsApp capturado exacto                     | 100%    | ✅ 100%   | El backend rechaza todo número mal formado; nunca se guardó uno incorrecto |

**Nota sobre la muestra:** cada escenario se corrió una vez. Para afirmar las metas de "9 de 10" con más confianza, la v2 repetirá cada escenario varias veces, porque el LLM no responde siempre igual.

## 3. Métricas

| Métrica                         | Valor     | Cómo se calculó                                                          |
| ------------------------------- | --------- | ------------------------------------------------------------------------ |
| Latencia promedio de respuesta  | Pendiente | Logs de llamadas de Vapi                                                 |
| Latencia de las tools (backend) | Pendiente | `latency_ms` en Langfuse                                                 |
| WER del reconocimiento de voz   | Pendiente | `scripts/eval_metrics.py` con frases de referencia                       |
| Costo promedio por llamada      | Pendiente | `avg(cost_usd)` de la tabla `calls` (una llamada de 34 s costó US$ 0,04) |

## 4. Hallazgos y ajustes

| Hallazgo                                                                                   | Escenario       | Ajuste                                                                        | Estado       |
| ------------------------------------------------------------------------------------------ | --------------- | ----------------------------------------------------------------------------- | ------------ |
| Enviaba 10 dígitos a la tool aunque confirmaba 9 en voz alta                               | E12             | Error accionable en el backend + conteo de dígitos en el prompt               | ✅ v1.1      |
| Ofrecía derivar casos de áreas que el estudio no atiende                                   | E6              | Regla propia para áreas no atendidas                                          | ✅ v1.2      |
| Decía "mañana" o "el próximo día hábil" sin nombrar la fecha                               | E3, E4          | Nombrar siempre el día y la fecha                                             | ✅ v1.2      |
| El refuerzo de keywords hacía "oír" la palabra donde no estaba ("Lex correcto", "Andina,") | E9, E12         | Se quitaron los nombres propios de los keywords                               | ✅ v1.2      |
| La derivación salía sin área y sin decir quién estaba afectado                             | E8              | La regla pasó del prompt a la descripción de los parámetros de la tool        | ✅ v1.3      |
| El ASR entendió "Cuyo" en vez de "Julio"                                                   | Reserva por voz | El prompt pide repetir un nombre que no suena a nombre de persona             | ✅ v1.1      |
| El ASR a veces corta las primeras palabras del cliente                                     | E8              | Ajustar en Vapi cuánto espera antes de escuchar                               | Pendiente v2 |
| El LLM a veces cuenta mal los dígitos y pide repetir un número correcto                    | E8              | El backend garantiza el número; mejora futura: validar el número con una tool | Pendiente v2 |
| La transcripción de la voz de Lucía tiene errores ("12 200 soles", "Lex and D.")           | E4, E5          | Limitación conocida: para revisar una llamada, usar la grabación de Vapi      | Limitación   |
| El resumen del reporte de Vapi llega vacío                                                 | —               | Activar el análisis de la llamada en Vapi                                     | Pendiente v2 |
