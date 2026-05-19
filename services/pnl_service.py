from datetime import date

import pandas as pd
from sqlalchemy import func
from sqlalchemy.orm import Session

from database.models import (
    CompanyExpense,
    DoctorExpense,
    DoctorMaster,
    DoctorPayment,
    MedicalMaster,
    PaymentCollection,
    SalesData,
    SalesPersonExpense,
    VisitDetail,
    VisitMaster,
)
from services.commission_service import aggregate_doctor_commission, get_doctor_visit_lines
from utils.profit import line_amounts


def get_doctor_pnl(session: Session, doctor_id: int, from_date: date, to_date: date) -> dict:
    lines = get_doctor_visit_lines(session, doctor_id, from_date, to_date)
    total_commission = sum(l["commission_amount"] for l in lines)
    total_sales = sum(l["sales_amount"] for l in lines)
    total_cost = sum(l["cost_amount"] for l in lines)
    total_profit = sum(l["profit"] for l in lines)

    expenses = (
        session.query(DoctorExpense)
        .filter(
            DoctorExpense.doctor_id == doctor_id,
            DoctorExpense.expense_date >= from_date,
            DoctorExpense.expense_date <= to_date,
        )
        .all()
    )
    deductible = sum(e.amount for e in expenses if e.deduct_from_commission)
    company_expense_only = sum(e.amount for e in expenses if not e.deduct_from_commission)

    payments = (
        session.query(DoctorPayment)
        .filter(
            DoctorPayment.doctor_id == doctor_id,
            DoctorPayment.payment_date >= from_date,
            DoctorPayment.payment_date <= to_date,
        )
        .all()
    )
    total_payments = sum(p.amount for p in payments)

    balance = total_commission - deductible - total_payments

    medical_wise = {}
    product_wise = {}
    for l in lines:
        m = l["medical_name"]
        p = l["product_name"]
        medical_wise[m] = medical_wise.get(m, 0) + l["sales_amount"]
        product_wise[p] = product_wise.get(p, 0) + l["sold_qty"]

    return {
        "lines": lines,
        "total_sales": total_sales,
        "total_cost": total_cost,
        "total_profit": total_profit,
        "total_commission": total_commission,
        "deductible_expenses": deductible,
        "company_expenses": company_expense_only,
        "total_payments": total_payments,
        "balance": balance,
        "medical_wise": medical_wise,
        "product_wise": product_wise,
        "expenses": expenses,
        "payments": payments,
    }


def get_medical_ledger(session: Session, medical_id: int, from_date: date, to_date: date) -> dict:
    sales = (
        session.query(SalesData)
        .filter(
            SalesData.medical_id == medical_id,
            SalesData.bill_date >= from_date,
            SalesData.bill_date <= to_date,
        )
        .all()
    )

    collections = (
        session.query(PaymentCollection)
        .filter(
            PaymentCollection.medical_id == medical_id,
            PaymentCollection.collection_date >= from_date,
            PaymentCollection.collection_date <= to_date,
        )
        .all()
    )
    total_sales = sum(s.amount for s in sales)
    total_collection = sum(c.amount for c in collections)
    outstanding = total_sales - total_collection
    return {
        "sales": sales,
        "collections": collections,
        "total_sales": total_sales,
        "total_collection": total_collection,
        "outstanding": outstanding,
    }


def get_visit_profit_totals(session: Session, from_date: date, to_date: date) -> dict:
    """Aggregate sales, cost, profit from visit stock (sold qty)."""
    rows = (
        session.query(VisitDetail.sold_qty, VisitDetail.rate, VisitDetail.cost)
        .join(VisitMaster)
        .filter(
            VisitMaster.visit_date >= from_date,
            VisitMaster.visit_date <= to_date,
        )
        .all()
    )
    sales_amount = 0.0
    cost_amount = 0.0
    for sold_qty, rate, cost in rows:
        s, c, _ = line_amounts(sold_qty, rate, cost)
        sales_amount += s
        cost_amount += c
    gross_profit = sales_amount - cost_amount
    return {
        "sales_amount": sales_amount,
        "cost_amount": cost_amount,
        "gross_profit": gross_profit,
    }


def get_company_pnl(session: Session, from_date: date, to_date: date) -> dict:
    profit_totals = get_visit_profit_totals(session, from_date, to_date)
    sales_amount = profit_totals["sales_amount"]
    cost_amount = profit_totals["cost_amount"]
    gross_profit = profit_totals["gross_profit"]

    doctors = session.query(DoctorMaster).filter_by(is_active=True).all()
    total_doctor_commission = 0
    for d in doctors:
        total_doctor_commission += aggregate_doctor_commission(session, d.id, from_date, to_date)

    doctor_expenses = (
        session.query(func.coalesce(func.sum(DoctorExpense.amount), 0))
        .filter(
            DoctorExpense.expense_date >= from_date,
            DoctorExpense.expense_date <= to_date,
        )
        .scalar()
    ) or 0

    sales_expenses = (
        session.query(func.coalesce(func.sum(SalesPersonExpense.amount), 0))
        .filter(
            SalesPersonExpense.expense_date >= from_date,
            SalesPersonExpense.expense_date <= to_date,
        )
        .scalar()
    ) or 0

    company_expenses = (
        session.query(CompanyExpense)
        .filter(
            CompanyExpense.expense_date >= from_date,
            CompanyExpense.expense_date <= to_date,
        )
        .all()
    )
    company_expense_total = sum(e.amount for e in company_expenses)
    by_category = {}
    for e in company_expenses:
        by_category[e.expense_category] = by_category.get(e.expense_category, 0) + e.amount

    operating_expenses = (
        total_doctor_commission + float(doctor_expenses) + float(sales_expenses) + company_expense_total
    )
    net_profit = gross_profit - operating_expenses

    return {
        "sales_amount": sales_amount,
        "cost_amount": cost_amount,
        "gross_profit": gross_profit,
        "revenue": sales_amount,  # alias for PDF/backward compat
        "doctor_commission": total_doctor_commission,
        "doctor_expenses": float(doctor_expenses),
        "sales_person_expenses": float(sales_expenses),
        "company_expenses": company_expense_total,
        "company_expense_breakdown": by_category,
        "total_expenses": operating_expenses,
        "net_profit": net_profit,
    }


def get_outstanding_report(session: Session) -> pd.DataFrame:
    medicals = session.query(MedicalMaster).filter_by(is_active=True).all()
    rows = []
    for m in medicals:
        total_sales = (
            session.query(func.coalesce(func.sum(SalesData.amount), 0))
            .filter_by(medical_id=m.id)
            .scalar()
        ) or 0

        total_collected = (
            session.query(func.coalesce(func.sum(PaymentCollection.amount), 0))
            .filter_by(medical_id=m.id)
            .scalar()
        ) or 0
        rows.append({
            "Medical": m.medical_name,
            "Area": m.area.area_name if m.area else "",
            "Total Sales": total_sales,
            "Total Collection": total_collected,
            "Outstanding": total_sales - total_collected,
        })
    return pd.DataFrame(rows)
