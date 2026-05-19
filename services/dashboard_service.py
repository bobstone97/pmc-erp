from datetime import date, timedelta

import pandas as pd
from sqlalchemy import extract, func
from sqlalchemy.orm import Session

from database.models import (
    DoctorExpense,
    DoctorMaster,
    MedicalMaster,
    PaymentCollection,
    SalesData,
    SalesPersonExpense,
    VisitDetail,
    VisitMaster,
)
from services.pnl_service import get_company_pnl, get_outstanding_report


def get_dashboard_metrics(session: Session, from_date: date, to_date: date) -> dict:
    total_sales = (
        session.query(func.coalesce(func.sum(SalesData.amount), 0))
        .filter(SalesData.bill_date >= from_date, SalesData.bill_date <= to_date)
        .scalar()
    ) or 0

    total_collection = (
        session.query(func.coalesce(func.sum(PaymentCollection.amount), 0))
        .filter(
            PaymentCollection.collection_date >= from_date,
            PaymentCollection.collection_date <= to_date,
        )
        .scalar()
    ) or 0

    outstanding_df = get_outstanding_report(session)
    outstanding = outstanding_df["Outstanding"].sum() if not outstanding_df.empty else 0

    pnl = get_company_pnl(session, from_date, to_date)
    doctor_expense = (
        session.query(func.coalesce(func.sum(DoctorExpense.amount), 0))
        .filter(
            DoctorExpense.expense_date >= from_date,
            DoctorExpense.expense_date <= to_date,
        )
        .scalar()
    ) or 0
    sales_expense = (
        session.query(func.coalesce(func.sum(SalesPersonExpense.amount), 0))
        .filter(
            SalesPersonExpense.expense_date >= from_date,
            SalesPersonExpense.expense_date <= to_date,
        )
        .scalar()
    ) or 0

    return {
        "total_sales": float(total_sales),
        "total_collection": float(total_collection),
        "outstanding": float(outstanding),
        "sales_amount": pnl["sales_amount"],
        "cost_amount": pnl["cost_amount"],
        "gross_profit": pnl["gross_profit"],
        "net_profit": pnl["net_profit"],
        "doctor_commission": pnl["doctor_commission"],
        "company_expense": pnl["company_expenses"] + float(doctor_expense),
        "sales_person_expense": float(sales_expense),
    }


def sales_by_doctor_chart(session: Session, from_date: date, to_date: date) -> pd.DataFrame:
    rows = (
        session.query(
            DoctorMaster.doctor_name,
            func.sum(VisitDetail.sold_qty * VisitDetail.rate).label("sales"),
        )
        .join(VisitMaster, VisitMaster.doctor_id == DoctorMaster.id)
        .join(VisitDetail, VisitDetail.visit_id == VisitMaster.id)
        .filter(VisitMaster.visit_date >= from_date, VisitMaster.visit_date <= to_date)
        .group_by(DoctorMaster.doctor_name)
        .all()
    )
    return pd.DataFrame(rows, columns=["Doctor", "Sales"])


def sales_by_medical_chart(session: Session, from_date: date, to_date: date) -> pd.DataFrame:
    rows = (
        session.query(
            MedicalMaster.medical_name,
            func.sum(SalesData.amount).label("sales"),
        )
        .join(SalesData, SalesData.medical_id == MedicalMaster.id)
        .filter(SalesData.bill_date >= from_date, SalesData.bill_date <= to_date)
        .group_by(MedicalMaster.medical_name)
        .all()
    )
    return pd.DataFrame(rows, columns=["Medical", "Sales"])


def product_wise_sales_chart(session: Session, from_date: date, to_date: date) -> pd.DataFrame:
    from database.models import ProductMaster

    rows = (
        session.query(
            ProductMaster.product_name,
            func.sum(VisitDetail.sold_qty).label("qty"),
        )
        .join(VisitDetail, VisitDetail.product_id == ProductMaster.id)
        .join(VisitMaster)
        .filter(VisitMaster.visit_date >= from_date, VisitMaster.visit_date <= to_date)
        .group_by(ProductMaster.product_name)
        .all()
    )
    return pd.DataFrame(rows, columns=["Product", "Qty"])


def monthly_trend_chart(session: Session, year: int) -> pd.DataFrame:
    rows = (
        session.query(
            extract("month", SalesData.bill_date).label("month"),
            func.sum(SalesData.amount).label("sales"),
        )
        .filter(extract("year", SalesData.bill_date) == year)
        .group_by(extract("month", SalesData.bill_date))
        .order_by(extract("month", SalesData.bill_date))
        .all()
    )
    return pd.DataFrame(rows, columns=["Month", "Sales"])


def top_lists(session: Session, from_date: date, to_date: date) -> dict:
    by_doctor = sales_by_doctor_chart(session, from_date, to_date).sort_values("Sales", ascending=False).head(5)
    by_medical = sales_by_medical_chart(session, from_date, to_date).sort_values("Sales", ascending=False).head(5)
    outstanding = get_outstanding_report(session).sort_values("Outstanding", ascending=False).head(5)
    expense_doctors = (
        session.query(
            DoctorMaster.doctor_name,
            func.sum(DoctorExpense.amount).label("expense"),
        )
        .join(DoctorExpense)
        .filter(
            DoctorExpense.expense_date >= from_date,
            DoctorExpense.expense_date <= to_date,
        )
        .group_by(DoctorMaster.doctor_name)
        .order_by(func.sum(DoctorExpense.amount).desc())
        .limit(5)
        .all()
    )
    return {
        "top_doctors": by_doctor,
        "top_medicals": by_medical,
        "highest_outstanding": outstanding,
        "highest_expense_doctors": pd.DataFrame(expense_doctors, columns=["Doctor", "Expense"]),
    }
