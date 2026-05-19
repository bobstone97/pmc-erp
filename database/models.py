from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="sales")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    permissions: Mapped[list["UserPermission"]] = relationship(back_populates="user")
    sales_expenses: Mapped[list["SalesPersonExpense"]] = relationship(back_populates="user")


class UserPermission(Base):
    __tablename__ = "user_permissions"
    __table_args__ = (UniqueConstraint("user_id", "page_key", name="uq_user_page"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    page_key: Mapped[str] = mapped_column(String(50), nullable=False)
    can_view: Mapped[bool] = mapped_column(Boolean, default=True)
    can_edit: Mapped[bool] = mapped_column(Boolean, default=False)

    user: Mapped["User"] = relationship(back_populates="permissions")


class AreaMaster(Base):
    __tablename__ = "area_master"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    area_name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class ProductMaster(Base):
    __tablename__ = "product_master"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_name: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    mrp: Mapped[float] = mapped_column(Float, default=0)
    ptr: Mapped[float] = mapped_column(Float, default=0)
    pts: Mapped[float] = mapped_column(Float, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class DoctorMaster(Base):
    __tablename__ = "doctor_master"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    doctor_name: Mapped[str] = mapped_column(String(200), nullable=False)
    speciality: Mapped[str | None] = mapped_column(String(120))
    mobile: Mapped[str | None] = mapped_column(String(20))
    area_id: Mapped[int | None] = mapped_column(ForeignKey("area_master.id"))
    commission_type: Mapped[str] = mapped_column(String(30), default="MRP_PERCENT")
    commission_value: Mapped[float] = mapped_column(Float, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    area: Mapped["AreaMaster | None"] = relationship()
    mappings: Mapped[list["MappingMaster"]] = relationship(back_populates="doctor")
    expenses: Mapped[list["DoctorExpense"]] = relationship(back_populates="doctor")
    payments: Mapped[list["DoctorPayment"]] = relationship(back_populates="doctor")
    visits: Mapped[list["VisitMaster"]] = relationship(back_populates="doctor")


class MedicalMaster(Base):
    __tablename__ = "medical_master"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    medical_name: Mapped[str] = mapped_column(String(200), nullable=False)
    area_id: Mapped[int | None] = mapped_column(ForeignKey("area_master.id"))
    contact_person: Mapped[str | None] = mapped_column(String(120))
    mobile: Mapped[str | None] = mapped_column(String(20))
    address: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    area: Mapped["AreaMaster | None"] = relationship()
    mappings: Mapped[list["MappingMaster"]] = relationship(back_populates="medical")
    sales: Mapped[list["SalesData"]] = relationship(back_populates="medical")
    collections: Mapped[list["PaymentCollection"]] = relationship(back_populates="medical")
    visits: Mapped[list["VisitMaster"]] = relationship(back_populates="medical")


class MappingMaster(Base):
    __tablename__ = "mapping_master"
    __table_args__ = (
        UniqueConstraint("doctor_id", "medical_id", "product_id", name="uq_mapping"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctor_master.id"), nullable=False)
    medical_id: Mapped[int] = mapped_column(ForeignKey("medical_master.id"), nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey("product_master.id"), nullable=False)
    opening_stock: Mapped[float] = mapped_column(Float, default=0)
    opening_date: Mapped[date | None] = mapped_column(Date)
    current_stock: Mapped[float] = mapped_column(Float, default=0)
    rate: Mapped[float] = mapped_column(Float, default=0)
    cost: Mapped[float] = mapped_column(Float, default=0)
    commission_type_override: Mapped[str | None] = mapped_column(String(30))
    commission_value_override: Mapped[float | None] = mapped_column(Float)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    doctor: Mapped["DoctorMaster"] = relationship(back_populates="mappings")
    medical: Mapped["MedicalMaster"] = relationship(back_populates="mappings")
    product: Mapped["ProductMaster"] = relationship()


class SalesData(Base):
    __tablename__ = "sales_data"
    __table_args__ = (
        UniqueConstraint(
            "medical_id", "product_id", "bill_no", "bill_date",
            name="uq_sales_bill",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    medical_id: Mapped[int] = mapped_column(ForeignKey("medical_master.id"), nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey("product_master.id"), nullable=False)
    qty: Mapped[float] = mapped_column(Float, nullable=False)
    rate: Mapped[float] = mapped_column(Float, default=0)
    mrp: Mapped[float] = mapped_column(Float, default=0)
    cost: Mapped[float] = mapped_column(Float, default=0)
    bill_date: Mapped[date] = mapped_column(Date, nullable=False)
    bill_no: Mapped[str] = mapped_column(String(80), default="")
    amount: Mapped[float] = mapped_column(Float, default=0)
    profit: Mapped[float] = mapped_column(Float, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    medical: Mapped["MedicalMaster"] = relationship(back_populates="sales")
    product: Mapped["ProductMaster"] = relationship()


class VisitMaster(Base):
    __tablename__ = "visit_master"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctor_master.id"), nullable=False)
    medical_id: Mapped[int] = mapped_column(ForeignKey("medical_master.id"), nullable=False)
    visit_date: Mapped[date] = mapped_column(Date, nullable=False)
    from_date: Mapped[date] = mapped_column(Date, nullable=False)
    to_date: Mapped[date] = mapped_column(Date, nullable=False)
    remarks: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    doctor: Mapped["DoctorMaster"] = relationship(back_populates="visits")
    medical: Mapped["MedicalMaster"] = relationship(back_populates="visits")
    details: Mapped[list["VisitDetail"]] = relationship(
        back_populates="visit", cascade="all, delete-orphan"
    )


class VisitDetail(Base):
    __tablename__ = "visit_details"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    visit_id: Mapped[int] = mapped_column(ForeignKey("visit_master.id"), nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey("product_master.id"), nullable=False)
    opening_stock: Mapped[float] = mapped_column(Float, default=0)
    supply_qty: Mapped[float] = mapped_column(Float, default=0)
    current_stock: Mapped[float] = mapped_column(Float, default=0)
    sold_qty: Mapped[float] = mapped_column(Float, default=0)
    rate: Mapped[float] = mapped_column(Float, default=0)
    cost: Mapped[float] = mapped_column(Float, default=0)
    mrp: Mapped[float] = mapped_column(Float, default=0)

    visit: Mapped["VisitMaster"] = relationship(back_populates="details")
    product: Mapped["ProductMaster"] = relationship()


class StockTransaction(Base):
    __tablename__ = "stock_transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    visit_detail_id: Mapped[int | None] = mapped_column(ForeignKey("visit_details.id"))
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctor_master.id"))
    medical_id: Mapped[int] = mapped_column(ForeignKey("medical_master.id"))
    product_id: Mapped[int] = mapped_column(ForeignKey("product_master.id"))
    transaction_date: Mapped[date] = mapped_column(Date)
    opening_stock: Mapped[float] = mapped_column(Float, default=0)
    supply_qty: Mapped[float] = mapped_column(Float, default=0)
    current_stock: Mapped[float] = mapped_column(Float, default=0)
    sold_qty: Mapped[float] = mapped_column(Float, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class DoctorExpense(Base):
    __tablename__ = "doctor_expense"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctor_master.id"), nullable=False)
    expense_date: Mapped[date] = mapped_column(Date, nullable=False)
    expense_type: Mapped[str] = mapped_column(String(50), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    deduct_from_commission: Mapped[bool] = mapped_column(Boolean, default=True)
    remarks: Mapped[str | None] = mapped_column(Text)
    attachment_path: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    doctor: Mapped["DoctorMaster"] = relationship(back_populates="expenses")


class SalesPersonExpense(Base):
    __tablename__ = "sales_person_expense"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    expense_date: Mapped[date] = mapped_column(Date, nullable=False)
    expense_type: Mapped[str] = mapped_column(String(50), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    remarks: Mapped[str | None] = mapped_column(Text)
    attachment_path: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="sales_expenses")


class DoctorPayment(Base):
    __tablename__ = "doctor_payment"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctor_master.id"), nullable=False)
    payment_date: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    payment_mode: Mapped[str] = mapped_column(String(30), default="Cash")
    remarks: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    doctor: Mapped["DoctorMaster"] = relationship(back_populates="payments")


class PaymentCollection(Base):
    __tablename__ = "payment_collection"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    medical_id: Mapped[int] = mapped_column(ForeignKey("medical_master.id"), nullable=False)
    receipt_number: Mapped[str] = mapped_column(String(80), nullable=False)
    collection_date: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    payment_mode: Mapped[str] = mapped_column(String(30), default="Cash")
    bank: Mapped[str | None] = mapped_column(String(120))
    remarks: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    medical: Mapped["MedicalMaster"] = relationship(back_populates="collections")
    allocations: Mapped[list["PaymentAllocation"]] = relationship(
        back_populates="collection", cascade="all, delete-orphan"
    )


class PaymentAllocation(Base):
    __tablename__ = "payment_allocation"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    collection_id: Mapped[int] = mapped_column(ForeignKey("payment_collection.id"), nullable=False)
    bill_reference: Mapped[str | None] = mapped_column(String(120))
    allocated_amount: Mapped[float] = mapped_column(Float, default=0)
    remarks: Mapped[str | None] = mapped_column(Text)

    collection: Mapped["PaymentCollection"] = relationship(back_populates="allocations")


class CompanyExpense(Base):
    __tablename__ = "company_expense"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    expense_date: Mapped[date] = mapped_column(Date, nullable=False)
    expense_category: Mapped[str] = mapped_column(String(80), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    remarks: Mapped[str | None] = mapped_column(Text)
    attachment_path: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class OpeningStock(Base):
    """Historical opening stock snapshots per mapping."""
    __tablename__ = "opening_stock"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    mapping_id: Mapped[int] = mapped_column(ForeignKey("mapping_master.id"), nullable=False)
    opening_stock: Mapped[float] = mapped_column(Float, default=0)
    opening_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
