from datetime import date, timedelta

from sqlalchemy import desc
from sqlalchemy.orm import Session

from database.models import MappingMaster, StockTransaction, VisitDetail, VisitMaster
from services.sales_service import get_supply_qty


def get_previous_visit(session: Session, doctor_id: int, medical_id: int) -> VisitMaster | None:
    return (
        session.query(VisitMaster)
        .filter_by(doctor_id=doctor_id, medical_id=medical_id)
        .order_by(desc(VisitMaster.visit_date))
        .first()
    )


def calculate_visit_cycle(session: Session, doctor_id: int, medical_id: int, visit_date: date):
    prev = get_previous_visit(session, doctor_id, medical_id)
    if prev:
        from_date = prev.visit_date + timedelta(days=1)
    else:
        mappings = (
            session.query(MappingMaster)
            .filter_by(doctor_id=doctor_id, medical_id=medical_id)
            .all()
        )
        dates = [m.opening_date for m in mappings if m.opening_date]
        from_date = min(dates) if dates else visit_date
    to_date = visit_date
    return from_date, to_date


def check_cycle_overlap(session: Session, doctor_id: int, medical_id: int, visit_date: date) -> bool:
    prev = get_previous_visit(session, doctor_id, medical_id)
    if prev and visit_date <= prev.visit_date:
        return True
    return False


def get_earliest_visit_date(session: Session, doctor_id: int, medical_id: int) -> date | None:
    """First allowed visit date (day after last visit), or None if no prior visit."""
    prev = get_previous_visit(session, doctor_id, medical_id)
    if prev:
        return prev.visit_date + timedelta(days=1)
    return None


def get_mapped_products(session: Session, doctor_id: int, medical_id: int):
    return (
        session.query(MappingMaster)
        .filter_by(doctor_id=doctor_id, medical_id=medical_id)
        .all()
    )


def build_visit_stock_rows(
    session: Session,
    doctor_id: int,
    medical_id: int,
    visit_date: date,
) -> list[dict]:
    from_date, to_date = calculate_visit_cycle(session, doctor_id, medical_id, visit_date)
    mappings = get_mapped_products(session, doctor_id, medical_id)
    rows = []
    for m in mappings:
        prev_detail = (
            session.query(VisitDetail)
            .join(VisitMaster)
            .filter(
                VisitMaster.doctor_id == doctor_id,
                VisitMaster.medical_id == medical_id,
                VisitDetail.product_id == m.product_id,
            )
            .order_by(desc(VisitMaster.visit_date))
            .first()
        )
        opening = prev_detail.current_stock if prev_detail else m.opening_stock
        supply = get_supply_qty(session, medical_id, m.product_id, from_date, to_date)
        max_stock = opening + supply
        rows.append({
            "product_id": m.product_id,
            "product_name": m.product.product_name if m.product else "",
            "opening_stock": opening,
            "supply_qty": supply,
            "current_stock": m.current_stock,
            "max_stock": max_stock,
            "rate": m.rate,
            "cost": m.cost,
            "mrp": m.product.mrp if m.product else 0,
        })
    return rows


def save_visit(
    session: Session,
    doctor_id: int,
    medical_id: int,
    visit_date: date,
    line_items: list[dict],
    remarks: str | None,
    created_by: int | None,
) -> VisitMaster:
    if check_cycle_overlap(session, doctor_id, medical_id, visit_date):
        raise ValueError("Visit date overlaps with previous visit cycle.")

    from_date, to_date = calculate_visit_cycle(session, doctor_id, medical_id, visit_date)
    visit = VisitMaster(
        doctor_id=doctor_id,
        medical_id=medical_id,
        visit_date=visit_date,
        from_date=from_date,
        to_date=to_date,
        remarks=remarks,
        created_by=created_by,
    )
    session.add(visit)
    session.flush()

    for item in line_items:
        opening = float(item["opening_stock"])
        supply = float(item["supply_qty"])
        current = float(item["current_stock"])
        max_stock = opening + supply
        if current > max_stock:
            raise ValueError(
                f"Current stock ({current}) cannot exceed opening + supply ({max_stock}) "
                f"for product id {item['product_id']}"
            )
        sold = opening + supply - current
        detail = VisitDetail(
            visit_id=visit.id,
            product_id=item["product_id"],
            opening_stock=opening,
            supply_qty=supply,
            current_stock=current,
            sold_qty=sold,
            rate=item.get("rate", 0),
            cost=item.get("cost", 0),
            mrp=item.get("mrp", 0),
        )
        session.add(detail)
        session.flush()

        mapping = (
            session.query(MappingMaster)
            .filter_by(
                doctor_id=doctor_id,
                medical_id=medical_id,
                product_id=item["product_id"],
            )
            .first()
        )
        if mapping:
            mapping.current_stock = current

        session.add(
            StockTransaction(
                visit_detail_id=detail.id,
                doctor_id=doctor_id,
                medical_id=medical_id,
                product_id=item["product_id"],
                transaction_date=visit_date,
                opening_stock=opening,
                supply_qty=supply,
                current_stock=current,
                sold_qty=sold,
            )
        )
    return visit


def get_visit_history(session: Session, doctor_id: int | None = None, medical_id: int | None = None):
    q = session.query(VisitMaster)
    if doctor_id:
        q = q.filter_by(doctor_id=doctor_id)
    if medical_id:
        q = q.filter_by(medical_id=medical_id)
    return q.order_by(desc(VisitMaster.visit_date)).all()
