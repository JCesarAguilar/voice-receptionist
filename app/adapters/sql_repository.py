"""Adaptador de salida: guarda las reservas en una base SQL con SQLModel."""

from datetime import datetime
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import Engine
from sqlmodel import Field, Session, SQLModel, col, create_engine, select

from app.domain.models import Area, Booking, BookingStatus, Client, Modality


class BookingRow(SQLModel, table=True):
    """Cómo se guarda una reserva en la tabla `bookings`."""

    __tablename__ = "bookings"  # type: ignore[assignment]  # falso positivo de SQLModel

    id: UUID = Field(primary_key=True)
    client_name: str
    client_whatsapp: str
    area: str
    modality: str
    start_at: datetime
    end_at: datetime
    summary: str
    price_cents: int
    status: str = Field(index=True)
    created_at: datetime = Field(index=True)
    calendar_event_id: str | None = None
    payment_order_id: str | None = Field(default=None, index=True, unique=True)
    confirmed_at: datetime | None = None
    late_payment_at: datetime | None = None


def make_engine(database_url: str) -> Engine:
    """Conecta con la base y crea la tabla si no existe."""
    is_sqlite = database_url.startswith("sqlite")
    connect_args = {"check_same_thread": False} if is_sqlite else {}
    engine = create_engine(database_url, connect_args=connect_args)
    SQLModel.metadata.create_all(engine)
    return engine


class SqlBookingRepository:
    """Cumple el puerto BookingRepository usando una base de datos real."""

    def __init__(self, engine: Engine, timezone: ZoneInfo) -> None:
        self._engine = engine
        self._timezone = timezone

    def add(self, booking: Booking) -> None:
        with Session(self._engine) as session:
            session.add(self._to_row(booking))
            session.commit()

    def get(self, booking_id: UUID) -> Booking | None:
        with Session(self._engine) as session:
            row = session.get(BookingRow, booking_id)
            return self._to_domain(row) if row else None

    def get_by_order_id(self, order_id: str) -> Booking | None:
        query = select(BookingRow).where(col(BookingRow.payment_order_id) == order_id)
        with Session(self._engine) as session:
            row = session.exec(query).first()
            return self._to_domain(row) if row else None

    def update(self, booking: Booking) -> None:
        with Session(self._engine) as session:
            session.merge(self._to_row(booking))
            session.commit()

    def pending_created_before(self, cutoff: datetime) -> list[Booking]:
        query = select(BookingRow).where(
            col(BookingRow.status) == BookingStatus.PENDING_PAYMENT.value,
            col(BookingRow.created_at) < cutoff,
        )
        with Session(self._engine) as session:
            return [self._to_domain(row) for row in session.exec(query).all()]

    def _from_db(self, moment: datetime) -> datetime:
        """SQLModel devuelve la hora en UTC; la pasamos a la zona del estudio."""
        return moment.astimezone(self._timezone)

    def _from_db_optional(self, moment: datetime | None) -> datetime | None:
        return self._from_db(moment) if moment else None

    @staticmethod
    def _to_row(booking: Booking) -> BookingRow:
        return BookingRow(
            id=booking.id,
            client_name=booking.client.name,
            client_whatsapp=booking.client.whatsapp,
            area=booking.area.value,
            modality=booking.modality.value,
            start_at=booking.start,
            end_at=booking.end,
            summary=booking.summary,
            price_cents=booking.price_cents,
            status=booking.status.value,
            created_at=booking.created_at,
            calendar_event_id=booking.calendar_event_id,
            payment_order_id=booking.payment_order_id,
            confirmed_at=booking.confirmed_at,
            late_payment_at=booking.late_payment_at,
        )

    def _to_domain(self, row: BookingRow) -> Booking:
        return Booking(
            id=row.id,
            client=Client(name=row.client_name, whatsapp=row.client_whatsapp),
            area=Area(row.area),
            modality=Modality(row.modality),
            start=self._from_db(row.start_at),
            end=self._from_db(row.end_at),
            summary=row.summary,
            price_cents=row.price_cents,
            status=BookingStatus(row.status),
            created_at=self._from_db(row.created_at),
            calendar_event_id=row.calendar_event_id,
            payment_order_id=row.payment_order_id,
            confirmed_at=self._from_db_optional(row.confirmed_at),
            late_payment_at=self._from_db_optional(row.late_payment_at),
        )
