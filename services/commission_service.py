from datetime import date

from sqlalchemy import func
from sqlalchemy.orm import Session

from database.models import (
    DoctorMaster,
    MappingMaster,
    PaymentCollection,
    ProductMaster,
    VisitDetail,
    VisitMaster,
)
from services.sales_service import get_supply_qty
from utils.profit import line_amounts


def resolve_commission_params(mapping: MappingMaster | None, doctor: DoctorMaster):
    if mapping and mapping.commission_type_override:
        return mapping.commission_type_override, mapping.commission_value_override or 0
    return doctor.commission_type, doctor.commission_value


def calculate_line_commission(
    commission_type: str,
    commission_value: float,
    sold_qty: float,
    mrp: float,
    ptr: float,
    rate: float,
    supply_qty: float,
    supply_value: float,
    collection_amount: float,
) -> float:
    ct = commission_type.upper()
    if ct == "SUPPLY":
        # % of supply value in visit window (supply_qty × rate)
        return supply_value * (commission_value / 100)
    if ct == "MRP_PERCENT":
        return sold_qty * mrp * (commission_value / 100)
    if ct == "PAYMENT":
        return collection_amount * (commission_value / 100)
    if ct == "TRADE":
        # % of sold value at invoice rate: Rate × Sold Qty × (Value ÷ 100)
        return rate * sold_qty * (commission_value / 100)
    if ct == "FIXED":
        return commission_value
    return sold_qty * rate * (commission_value / 100)


def get_doctor_visit_lines(
    session: Session,
    doctor_id: int,
    from_date: date,
    to_date: date,
) -> list[dict]:
    details = (
        session.query(VisitDetail, VisitMaster, ProductMaster, MappingMaster)
        .join(VisitMaster, VisitDetail.visit_id == VisitMaster.id)
        .join(ProductMaster, VisitDetail.product_id == ProductMaster.id)
        .outerjoin(
            MappingMaster,
            (MappingMaster.doctor_id == VisitMaster.doctor_id)
            & (MappingMaster.medical_id == VisitMaster.medical_id)
            & (MappingMaster.product_id == VisitDetail.product_id),
        )
        .filter(
            VisitMaster.doctor_id == doctor_id,
            VisitMaster.visit_date >= from_date,
            VisitMaster.visit_date <= to_date,
        )
        .all()
    )

    doctor = session.get(DoctorMaster, doctor_id)
    lines = []
    for detail, visit, product, mapping in details:
        ct, cv = resolve_commission_params(mapping, doctor)
        supply_qty = get_supply_qty(
            session, visit.medical_id, detail.product_id, visit.from_date, visit.to_date
        )
        supply_value = supply_qty * detail.rate
        collection = (
            session.query(func.coalesce(func.sum(PaymentCollection.amount), 0))
            .filter(
                PaymentCollection.medical_id == visit.medical_id,
                PaymentCollection.collection_date >= visit.from_date,
                PaymentCollection.collection_date <= visit.to_date,
            )
            .scalar()
        ) or 0

        commission = calculate_line_commission(
            ct, cv, detail.sold_qty, detail.mrp or product.mrp,
            product.ptr, detail.rate, supply_qty, supply_value, float(collection),
        )
        sales_amount, cost_amount, profit = line_amounts(
            detail.sold_qty, detail.rate, detail.cost
        )
        lines.append({
            "visit_date": visit.visit_date,
            "medical_id": visit.medical_id,
            "medical_name": visit.medical.medical_name if visit.medical else "",
            "product_id": detail.product_id,
            "product_name": product.product_name,
            "sold_qty": detail.sold_qty,
            "rate": detail.rate,
            "cost": detail.cost,
            "mrp": detail.mrp or product.mrp,
            "sales_amount": sales_amount,
            "cost_amount": cost_amount,
            "profit": profit,
            "commission_type": ct,
            "commission_value": cv,
            "commission_amount": commission,
        })
    return lines


def aggregate_doctor_commission(session: Session, doctor_id: int, from_date: date, to_date: date) -> float:
    lines = get_doctor_visit_lines(session, doctor_id, from_date, to_date)
    return sum(l["commission_amount"] for l in lines)
