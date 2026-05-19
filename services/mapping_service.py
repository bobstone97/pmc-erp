from datetime import date, datetime

from sqlalchemy.orm import Session

from database.models import MappingMaster, OpeningStock


def upsert_mapping(
    session: Session,
    doctor_id: int,
    medical_id: int,
    product_id: int,
    opening_stock: float = 0,
    opening_date: date | None = None,
    rate: float = 0,
    cost: float = 0,
    commission_type_override: str | None = None,
    commission_value_override: float | None = None,
    current_stock: float | None = None,
) -> MappingMaster:
    mapping = (
        session.query(MappingMaster)
        .filter_by(doctor_id=doctor_id, medical_id=medical_id, product_id=product_id)
        .first()
    )
    if mapping:
        mapping.opening_stock = opening_stock
        mapping.opening_date = opening_date
        mapping.rate = rate
        mapping.cost = cost
        mapping.commission_type_override = commission_type_override
        mapping.commission_value_override = commission_value_override
        if current_stock is not None:
            mapping.current_stock = current_stock
        mapping.updated_at = datetime.utcnow()
    else:
        mapping = MappingMaster(
            doctor_id=doctor_id,
            medical_id=medical_id,
            product_id=product_id,
            opening_stock=opening_stock,
            opening_date=opening_date,
            rate=rate,
            cost=cost,
            commission_type_override=commission_type_override,
            commission_value_override=commission_value_override,
            current_stock=current_stock if current_stock is not None else opening_stock,
        )
        session.add(mapping)
        session.flush()
    return mapping


def get_mapping(session: Session, mapping_id: int) -> MappingMaster | None:
    return session.get(MappingMaster, mapping_id)


def reset_mapping_current_stock(
    session: Session, mapping_id: int, *, use_opening: bool = True, value: float | None = None
) -> MappingMaster | None:
    """Set current stock to opening, to a fixed value, or to 0."""
    m = session.get(MappingMaster, mapping_id)
    if not m:
        return None
    if value is not None:
        m.current_stock = max(0.0, float(value))
    elif use_opening:
        m.current_stock = float(m.opening_stock or 0)
    else:
        m.current_stock = 0.0
    m.updated_at = datetime.utcnow()
    return m


def update_mapping_fields(
    session: Session,
    mapping_id: int,
    *,
    opening_stock: float | None = None,
    opening_date: date | None = None,
    rate: float | None = None,
    cost: float | None = None,
    commission_type_override: str | None = None,
    commission_value_override: float | None = None,
    clear_commission_override: bool = False,
) -> MappingMaster | None:
    """Update rate/cost and other fields on an existing mapping."""
    m = session.get(MappingMaster, mapping_id)
    if not m:
        return None
    if opening_stock is not None:
        m.opening_stock = opening_stock
    if opening_date is not None:
        m.opening_date = opening_date
    if rate is not None:
        m.rate = rate
    if cost is not None:
        m.cost = cost
    if clear_commission_override:
        m.commission_type_override = None
        m.commission_value_override = None
    else:
        if commission_type_override is not None:
            m.commission_type_override = commission_type_override or None
        if commission_value_override is not None:
            m.commission_value_override = commission_value_override
    m.updated_at = datetime.utcnow()
    return m


def get_mapping_by_keys(
    session: Session, doctor_id: int, medical_id: int, product_id: int
) -> MappingMaster | None:
    return (
        session.query(MappingMaster)
        .filter_by(doctor_id=doctor_id, medical_id=medical_id, product_id=product_id)
        .first()
    )


def delete_mapping(session: Session, mapping_id: int) -> bool:
    """Remove doctor–medical–product mapping and related opening_stock rows."""
    m = session.get(MappingMaster, mapping_id)
    if not m:
        return False
    session.query(OpeningStock).filter_by(mapping_id=mapping_id).delete()
    session.delete(m)
    return True
