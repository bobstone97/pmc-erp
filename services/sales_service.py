from datetime import date

import pandas as pd
from sqlalchemy import func
from sqlalchemy.orm import Session

from database.models import MedicalMaster, ProductMaster, SalesData
from utils.helpers import clean_string, parse_date
from utils.profit import line_amounts

# Normalized Excel header (lowercase) -> internal field
COLUMN_LOOKUP: dict[str, str] = {
    "party name": "medical",
    "customer name": "medical",
    "medical store": "medical",
    "store name": "medical",
    "party": "medical",
    "medical": "medical",
    "customer": "medical",
    "item name": "product",
    "product name": "product",
    "medicine name": "product",
    "medicine": "product",
    "item": "product",
    "product": "product",
    "bill no": "bill_no",
    "bill number": "bill_no",
    "invoice no": "bill_no",
    "invoice number": "bill_no",
    "bill date": "bill_date",
    "invoice date": "bill_date",
    "date": "bill_date",
    "quantity": "qty",
    "qty": "qty",
    "sale rate": "rate",
    "rate": "rate",
    "mrp": "mrp",
    "m r p": "mrp",
    "max retail price": "mrp",
    "purchase rate": "cost",
    "cost": "cost",
    "pts": "cost",
    "ptr": "ptr",
}

# Not mapped to bill_date / other fields
IGNORED_COLUMNS = {
    "expiry date",
    "exp date",
    "expiry",
    "month",
    "batch",
    "scheme",
    "disc",
    "discount",
    "free qty",
    "free quantity",
    "free",
    "sr no",
    "sno",
    "remarks",
}


def normalize_header(col) -> str:
    s = clean_string(col).lower()
    s = s.replace("#", "").replace(".", " ")
    return " ".join(s.split())


def map_upload_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Map distributor / billing software column names to internal fields."""
    rename_map = {}
    used_internal: set[str] = set()

    for col in df.columns:
        norm = normalize_header(col)
        if norm in IGNORED_COLUMNS:
            continue
        internal = COLUMN_LOOKUP.get(norm)
        if internal and internal not in used_internal:
            rename_map[col] = internal
            used_internal.add(internal)

    return df.rename(columns=rename_map)


def get_or_create_product(
    session: Session, product_name: str, mrp: float = 0, ptr: float = 0
) -> ProductMaster:
    product = session.query(ProductMaster).filter_by(product_name=product_name).first()
    if not product:
        product = ProductMaster(product_name=product_name, mrp=mrp, ptr=ptr)
        session.add(product)
        session.flush()
    else:
        if mrp > 0 and (product.mrp or 0) == 0:
            product.mrp = mrp
        if ptr > 0 and (product.ptr or 0) == 0:
            product.ptr = ptr
    return product


def get_or_create_medical(session: Session, medical_name: str) -> MedicalMaster:
    medical = session.query(MedicalMaster).filter_by(medical_name=medical_name).first()
    if not medical:
        medical = MedicalMaster(medical_name=medical_name)
        session.add(medical)
        session.flush()
    return medical


def resolve_mrp(
    session: Session,
    product_name: str,
    row_mrp: float,
    rate: float,
) -> tuple[float, str]:
    """
    Returns (mrp, source) where source is 'file' | 'master' | 'missing'.
    """
    if row_mrp and row_mrp > 0:
        return row_mrp, "file"
    existing = session.query(ProductMaster).filter_by(product_name=product_name).first()
    if existing and (existing.mrp or 0) > 0:
        return float(existing.mrp), "master"
    return 0.0, "missing"


def process_sales_upload(session: Session, df: pd.DataFrame) -> dict:
    """
    Supports standard and distributor Excel formats.

    Recognized headers include:
    Party Name / Medical Store, Item Name / Product, Date / Bill Date,
    Bill No, Qty, Rate, MRP, Cost.
    """
    df = map_upload_columns(df)

    required = ["medical", "product", "qty", "bill_date"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        friendly = {
            "medical": "Party Name / Medical Store",
            "product": "Item Name / Product",
            "bill_date": "Date / Bill Date",
            "qty": "Qty",
        }
        hint = ", ".join(friendly.get(c, c) for c in missing)
        return {
            "success": False,
            "message": f"Missing columns: {', '.join(missing)}. Expected: {hint}",
        }

    has_mrp_column = "mrp" in df.columns

    inserted = 0
    duplicates = 0
    merged_in_file = 0
    errors = []
    mrp_from_master = 0
    mrp_missing_rows = []

    # Step 1: Parse rows and merge duplicates within the same Excel file
    # (same Party + Item + Bill No + Date → sum Qty)
    aggregated: dict[tuple, dict] = {}

    for idx, row in df.iterrows():
        try:
            medical_name = clean_string(row.get("medical"))
            product_name = clean_string(row.get("product"))
            if not medical_name or not product_name:
                errors.append(f"Row {idx + 2}: Missing Party/Medical or Item/Product")
                continue

            qty = float(row.get("qty", 0) or 0)
            if qty <= 0:
                continue

            rate = float(row.get("rate", 0) or 0)
            row_mrp = float(row.get("mrp", 0) or 0) if has_mrp_column else 0.0
            cost = float(row.get("cost", 0) or 0)
            ptr = float(row.get("ptr", 0) or 0) if "ptr" in df.columns else 0.0

            bill_date = parse_date(row.get("bill_date"))
            if not bill_date:
                errors.append(f"Row {idx + 2}: Invalid date ({row.get('bill_date')})")
                continue

            bill_no = clean_string(row.get("bill_no", ""))
            if not bill_no:
                bill_no = f"AUTO-{medical_name}-{product_name}-{bill_date}"

            key = (medical_name.upper(), product_name.upper(), bill_no.upper(), bill_date)
            if key in aggregated:
                merged_in_file += 1
                agg = aggregated[key]
                old_qty = agg["qty"]
                new_qty = old_qty + qty
                if new_qty > 0:
                    agg["rate"] = (agg["rate"] * old_qty + rate * qty) / new_qty
                    agg["cost"] = (agg["cost"] * old_qty + cost * qty) / new_qty
                agg["qty"] = new_qty
                if row_mrp > 0:
                    agg["row_mrp"] = row_mrp
                if ptr > 0:
                    agg["ptr"] = ptr
                agg["source_rows"].append(idx + 2)
            else:
                aggregated[key] = {
                    "medical_name": medical_name,
                    "product_name": product_name,
                    "bill_no": bill_no,
                    "bill_date": bill_date,
                    "qty": qty,
                    "rate": rate,
                    "cost": cost,
                    "row_mrp": row_mrp,
                    "ptr": ptr,
                    "source_rows": [idx + 2],
                }
        except Exception as e:
            errors.append(f"Row {idx + 2}: {e}")

    # Step 2: Insert merged rows (skip if already in database)
    for agg in aggregated.values():
        try:
            medical_name = agg["medical_name"]
            product_name = agg["product_name"]
            qty = agg["qty"]
            rate = agg["rate"]
            cost = agg["cost"]
            row_mrp = agg["row_mrp"]
            ptr = agg["ptr"]
            bill_date = agg["bill_date"]
            bill_no = agg["bill_no"]
            src = agg["source_rows"]

            mrp, mrp_source = resolve_mrp(session, product_name, row_mrp, rate)
            if mrp_source == "master":
                mrp_from_master += 1
            elif mrp_source == "missing":
                mrp_missing_rows.append(f"Rows {src}: {product_name}")

            medical = get_or_create_medical(session, medical_name)
            product = get_or_create_product(session, product_name, mrp=mrp, ptr=ptr)
            if mrp > 0 and product.mrp != mrp:
                product.mrp = mrp

            exists = (
                session.query(SalesData)
                .filter_by(
                    medical_id=medical.id,
                    product_id=product.id,
                    bill_no=bill_no,
                    bill_date=bill_date,
                )
                .first()
            )
            if exists:
                duplicates += 1
                continue

            amount, _, profit = line_amounts(qty, rate, cost)
            session.add(
                SalesData(
                    medical_id=medical.id,
                    product_id=product.id,
                    qty=qty,
                    rate=rate,
                    mrp=mrp,
                    cost=cost,
                    bill_date=bill_date,
                    bill_no=bill_no,
                    amount=amount,
                    profit=profit,
                )
            )
            inserted += 1
        except Exception as e:
            errors.append(f"Rows {agg.get('source_rows', '?')}: {e}")

    warnings = []
    if merged_in_file:
        warnings.append(
            f"{merged_in_file} duplicate line(s) in Excel merged (same Party + Item + Bill + Date — Qty added)."
        )
    if not has_mrp_column:
        warnings.append(
            "Excel mein MRP column nahi thi — Product Master se MRP use hua jahan available tha. "
            "Baaki products ka MRP **Edit Product** tab se set karein."
        )
    if mrp_from_master:
        warnings.append(f"{mrp_from_master} rows: MRP Product Master se liya gaya.")
    if mrp_missing_rows:
        warnings.append(
            f"{len(mrp_missing_rows)} rows par MRP missing (commission ke liye zaroori). "
            "Product Master ya Edit Product se MRP add karein."
        )
        errors.extend(mrp_missing_rows[:15])
        if len(mrp_missing_rows) > 15:
            errors.append(f"... aur {len(mrp_missing_rows) - 15} rows")

    return {
        "success": True,
        "inserted": inserted,
        "duplicates": duplicates,
        "merged_in_file": merged_in_file,
        "errors": errors,
        "warnings": warnings,
        "has_mrp_column": has_mrp_column,
        "mrp_missing_count": len(mrp_missing_rows),
    }


def get_supply_qty(
    session: Session,
    medical_id: int,
    product_id: int,
    from_date: date,
    to_date: date,
) -> float:
    result = (
        session.query(func.coalesce(func.sum(SalesData.qty), 0))
        .filter(
            SalesData.medical_id == medical_id,
            SalesData.product_id == product_id,
            SalesData.bill_date >= from_date,
            SalesData.bill_date <= to_date,
        )
        .scalar()
    )
    return float(result or 0)


def get_sales_summary(session: Session, from_date: date | None = None, to_date: date | None = None):
    q = session.query(SalesData)
    if from_date:
        q = q.filter(SalesData.bill_date >= from_date)
    if to_date:
        q = q.filter(SalesData.bill_date <= to_date)
    rows = q.all()
    return rows


def recalc_sales_amounts(record: SalesData) -> None:
    record.amount, _, record.profit = line_amounts(record.qty, record.rate, record.cost)


def update_sales_record(
    session: Session,
    sales_id: int,
    qty: float,
    rate: float,
    mrp: float,
    cost: float,
    bill_date: date,
    bill_no: str,
    sync_product_mrp: bool = False,
) -> SalesData:
    record = session.get(SalesData, sales_id)
    if not record:
        raise ValueError("Sales record not found")

    duplicate = (
        session.query(SalesData)
        .filter(
            SalesData.medical_id == record.medical_id,
            SalesData.product_id == record.product_id,
            SalesData.bill_no == bill_no,
            SalesData.bill_date == bill_date,
            SalesData.id != sales_id,
        )
        .first()
    )
    if duplicate:
        raise ValueError("Duplicate bill: same medical, product, bill no and date already exists.")

    record.qty = qty
    record.rate = rate
    record.mrp = mrp
    record.cost = cost
    record.bill_date = bill_date
    record.bill_no = bill_no
    recalc_sales_amounts(record)

    if sync_product_mrp and record.product:
        record.product.mrp = mrp

    return record


def delete_sales_record(session: Session, sales_id: int) -> bool:
    record = session.get(SalesData, sales_id)
    if record:
        session.delete(record)
        return True
    return False
