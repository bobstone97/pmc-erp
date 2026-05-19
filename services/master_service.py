from datetime import timedelta

from sqlalchemy.orm import Session

from database.models import (
    AreaMaster,
    DoctorMaster,
    DoctorExpense,
    DoctorPayment,
    MappingMaster,
    MedicalMaster,
    PaymentCollection,
    SalesData,
    StockTransaction,
    VisitMaster,
)


def get_min_visit_date(session: Session, doctor_id: int, medical_id: int):
    """Earliest allowed visit date = day after last visit."""
    from services.stock_service import get_previous_visit

    prev = get_previous_visit(session, doctor_id, medical_id)
    if prev:
        return prev.visit_date + timedelta(days=1), prev.visit_date
    return None, None


def delete_doctor(session: Session, doctor_id: int, *, hard: bool = False) -> str:
    d = session.get(DoctorMaster, doctor_id)
    if not d:
        return "Doctor not found"
    has_data = (
        session.query(VisitMaster).filter_by(doctor_id=doctor_id).first()
        or session.query(MappingMaster).filter_by(doctor_id=doctor_id).first()
    )
    if has_data and hard:
        return "Cannot delete: doctor has visits or mappings. Deactivate instead."
    if hard and not has_data:
        session.query(DoctorExpense).filter_by(doctor_id=doctor_id).delete()
        session.query(DoctorPayment).filter_by(doctor_id=doctor_id).delete()
        session.delete(d)
        return "deleted"
    d.is_active = False
    return "deactivated"


def delete_medical(session: Session, medical_id: int, *, hard: bool = False) -> str:
    m = session.get(MedicalMaster, medical_id)
    if not m:
        return "Medical not found"
    has_data = (
        session.query(SalesData).filter_by(medical_id=medical_id).first()
        or session.query(VisitMaster).filter_by(medical_id=medical_id).first()
    )
    if has_data and hard:
        return "Cannot delete: medical has sales/visits. Merge into another medical or deactivate."
    if hard and not has_data:
        session.query(MappingMaster).filter_by(medical_id=medical_id).delete()
        session.query(PaymentCollection).filter_by(medical_id=medical_id).delete()
        session.delete(m)
        return "deleted"
    m.is_active = False
    return "deactivated"


def merge_medicals(session: Session, source_id: int, target_id: int) -> dict:
    """
    Move all data from closed/old medical into active/latest medical.
    On mapping conflict (same doctor+product), keep target mapping; drop source mapping.
    """
    if source_id == target_id:
        raise ValueError("Source and target medical cannot be the same.")

    source = session.get(MedicalMaster, source_id)
    target = session.get(MedicalMaster, target_id)
    if not source or not target:
        raise ValueError("Invalid medical store selected.")

    stats = {
        "sales": 0,
        "collections": 0,
        "visits": 0,
        "mappings_moved": 0,
        "mappings_dropped": 0,
    }

    stats["sales"] = (
        session.query(SalesData).filter_by(medical_id=source_id).update({"medical_id": target_id})
    )
    stats["collections"] = (
        session.query(PaymentCollection).filter_by(medical_id=source_id).update({"medical_id": target_id})
    )
    stats["visits"] = (
        session.query(VisitMaster).filter_by(medical_id=source_id).update({"medical_id": target_id})
    )
    session.query(StockTransaction).filter_by(medical_id=source_id).update({"medical_id": target_id})

    source_mappings = session.query(MappingMaster).filter_by(medical_id=source_id).all()
    for sm in source_mappings:
        conflict = (
            session.query(MappingMaster)
            .filter_by(
                doctor_id=sm.doctor_id,
                medical_id=target_id,
                product_id=sm.product_id,
            )
            .first()
        )
        if conflict:
            conflict.current_stock = max(conflict.current_stock or 0, sm.current_stock or 0)
            conflict.opening_stock = max(conflict.opening_stock or 0, sm.opening_stock or 0)
            session.delete(sm)
            stats["mappings_dropped"] += 1
        else:
            sm.medical_id = target_id
            stats["mappings_moved"] += 1

    source.is_active = False
    source.address = (source.address or "") + f" [Merged into {target.medical_name}]"

    return stats


def update_area(session: Session, area_id: int, area_name: str, is_active: bool) -> bool:
    a = session.get(AreaMaster, area_id)
    if not a:
        return False
    a.area_name = area_name.strip()
    a.is_active = is_active
    return True


def delete_area(session: Session, area_id: int) -> str:
    a = session.get(AreaMaster, area_id)
    if not a:
        return "Area not found"
    in_use = (
        session.query(DoctorMaster).filter_by(area_id=area_id).first()
        or session.query(MedicalMaster).filter_by(area_id=area_id).first()
    )
    if in_use:
        a.is_active = False
        return "deactivated (in use by doctor/medical)"
    session.delete(a)
    return "deleted"
