from app.domain.models import Area, HandoffReason
from app.services.handoff import HandoffService
from tests.factories import make_client
from tests.fakes import FakeMessaging

STAFF = "+51900000000"


def test_e8_urgent_handoff_sends_all_data_to_staff():
    messaging = FakeMessaging()
    service = HandoffService(messaging, STAFF)

    service.notify(
        reason=HandoffReason.URGENT,
        client=make_client(),
        area=Area.PENAL,
        summary="Su hijo fue detenido hace una hora",
    )

    to, text = messaging.sent[0]
    assert to == STAFF
    assert "urgencia" in text
    assert "Ana Torres" in text
    assert "+51987654321" in text
    assert "penal" in text
    assert "detenido" in text


def test_handoff_without_area_says_undefined():
    messaging = FakeMessaging()
    service = HandoffService(messaging, STAFF)

    service.notify(
        reason=HandoffReason.CLIENT_REQUEST,
        client=make_client(),
        summary="Quiere hablar con un abogado",
    )

    assert "sin definir" in messaging.sent[0][1]
