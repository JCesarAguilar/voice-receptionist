from app.api.tool_dispatcher import ToolDispatcher
from app.domain.ports import TimeRange
from app.schemas.tools import ToolCall, ToolResult
from tests.factories import LIMA, THURSDAY, at
from tests.fakes import FakeCalendar, RecordingTracer
from tests.test_booking import STAFF, Env, make_env


def make_dispatcher(env: Env) -> ToolDispatcher:
    return ToolDispatcher(env.availability, env.service, env.service._handoff, LIMA)


def call(name: str, **arguments) -> ToolCall:
    return ToolCall.model_validate(
        {"id": "call_1", "function": {"name": name, "arguments": arguments}}
    )


def ok(result: ToolResult) -> str:
    """La tool salió bien: devuelve el texto para el agente."""
    assert result.error is None, result.error
    assert result.result is not None
    return result.result


def failed(result: ToolResult) -> str:
    """La tool falló: devuelve el mensaje de error."""
    assert result.result is None, result.result
    assert result.error is not None
    return result.error


BOOKING_ARGS = {
    "area": "laboral",
    "start": "2026-11-12T10:00:00-05:00",
    "modality": "virtual",
    "client_name": "Ana Torres",
    "client_whatsapp": "+51 987 654 321",
    "summary": "Despido sin aviso",
}


def test_check_availability_lists_slots_with_exact_start():
    result = make_dispatcher(make_env()).run(
        call("check_availability", area="laboral", date="2026-11-12")
    )

    assert result.tool_call_id == "call_1"
    text = ok(result)
    assert "jueves 12 de noviembre a las 09:00" in text
    assert "start=2026-11-12T09:00:00-05:00" in text


def test_create_booking_holds_slot_and_sends_link():
    env = make_env()

    text = ok(make_dispatcher(env).run(call("create_booking", **BOOKING_ARGS)))

    assert "Reserva separada" in text
    assert "S/ 120.00" in text
    assert "/pagar/" in env.messaging.sent[0][1]


def test_start_without_timezone_is_taken_as_lima_time():
    env = make_env()
    args = {**BOOKING_ARGS, "start": "2026-11-12T10:00:00"}

    ok(make_dispatcher(env).run(call("create_booking", **args)))

    assert not env.availability.is_available(at(THURSDAY, 10))


def test_busy_slot_is_a_result_not_an_error():
    env = make_env(busy=[TimeRange(at(THURSDAY, 10), at(THURSDAY, 10, 45))])

    text = ok(make_dispatcher(env).run(call("create_booking", **BOOKING_ARGS)))

    assert "No se pudo reservar" in text


def test_e12_invalid_whatsapp_returns_readable_error():
    args = {**BOOKING_ARGS, "client_whatsapp": "987654"}

    error = failed(make_dispatcher(make_env()).run(call("create_booking", **args)))

    assert "WhatsApp" in error


def test_unknown_area_returns_readable_error():
    result = make_dispatcher(make_env()).run(
        call("check_availability", area="tributario", date="2026-11-12")
    )

    assert "area" in failed(result)


def test_e8_handoff_tool_notifies_staff():
    env = make_env()

    result = make_dispatcher(env).run(
        call(
            "handoff_to_human",
            reason="urgencia",
            client_name="Ana Torres",
            client_whatsapp="+51987654321",
            summary="Su hijo fue detenido",
            area="penal",
        )
    )

    assert "contactarán" in ok(result)
    assert env.messaging.sent[0][0] == STAFF


def test_unknown_tool_returns_error():
    result = make_dispatcher(make_env()).run(call("borrar_todo"))

    assert "no existe" in failed(result)


class BrokenCalendar(FakeCalendar):
    def busy_ranges(self, start, end):
        raise ConnectionError("Google no responde")


def test_unexpected_failure_suggests_handoff():
    env = make_env()
    env.availability._calendar = BrokenCalendar()

    result = make_dispatcher(env).run(
        call("check_availability", area="laboral", date="2026-11-12")
    )

    assert "derivar a una persona" in failed(result)


def test_every_tool_call_is_traced_with_its_call_id():
    env = make_env()
    tracer = RecordingTracer()
    dispatcher = ToolDispatcher(
        env.availability, env.service, env.service._handoff, LIMA, tracer=tracer
    )

    dispatcher.run(
        call("check_availability", area="laboral", date="2026-11-12"),
        call_id="vapi-call-1",
    )

    [traced] = tracer.calls
    assert traced["call_id"] == "vapi-call-1"
    assert traced["name"] == "check_availability"
    assert traced["ok"] is True
    assert traced["seconds"] >= 0


def test_failed_tool_is_traced_as_error():
    env = make_env()
    tracer = RecordingTracer()
    dispatcher = ToolDispatcher(
        env.availability, env.service, env.service._handoff, LIMA, tracer=tracer
    )

    dispatcher.run(call("tool_que_no_existe"))

    assert tracer.calls[0]["ok"] is False
