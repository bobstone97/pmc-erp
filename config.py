import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/pmc_erp",
)
SECRET_KEY = os.getenv("SECRET_KEY", "pmc-erp-dev-secret-change-in-production")

PAGE_KEYS = [
    "dashboard",
    "sales_upload",
    "product_master",
    "doctor_master",
    "medical_master",
    "area_master",
    "product_mapping",
    "stock_entry",
    "doctor_expense",
    "sales_expense",
    "doctor_payment",
    "payment_collection",
    "medical_ledger",
    "doctor_pnl",
    "company_pnl",
    "user_management",
    "company_expense",
]

PAGE_LABELS = {
    "dashboard": "Dashboard",
    "sales_upload": "Sales Upload",
    "product_master": "Product Master",
    "doctor_master": "Doctor Master",
    "medical_master": "Medical Master",
    "area_master": "Area Master",
    "product_mapping": "Product Mapping",
    "stock_entry": "Stock Entry / Visits",
    "doctor_expense": "Doctor Expenses",
    "sales_expense": "Sales Person Expenses",
    "doctor_payment": "Doctor Payments",
    "payment_collection": "Payment Collection",
    "medical_ledger": "Medical Ledger",
    "doctor_pnl": "Doctor PNL",
    "company_pnl": "Company PNL",
    "user_management": "User Management",
    "company_expense": "Company Expenses",
}

COMMISSION_TYPES = ["SUPPLY", "MRP_PERCENT", "PAYMENT", "TRADE", "FIXED"]

# How "Commission Value" is interpreted for each type (shown in Doctor Master UI)
COMMISSION_VALUE_HELP: dict[str, str] = {
    "SUPPLY": "**Percentage** of supply value in the visit period: (Supply Qty × Rate) × (Value ÷ 100). Example: Value `10` = 10% of supply amount.",
    "MRP_PERCENT": "**Percentage** of MRP on sold qty: Sold Qty × MRP × (Value ÷ 100). Example: Value `20` = 20%.",
    "PAYMENT": "**Percentage** of collections from that medical in the visit window: Collection × (Value ÷ 100). Example: Value `5` = 5%.",
    "TRADE": "**Percentage** of sold value at rate: Rate × Sold Qty × (Value ÷ 100). Example: Rate 100, Sold Qty 10, Value 20 → 100 × 10 × 20% = 200.",
    "FIXED": "**Rupees (Rs), not %** — fixed amount added **per product line** on each visit in Doctor PNL (not once per month unless you use one visit per month). Example: Value `40` = Rs 40 per line.",
}
DOCTOR_EXPENSE_TYPES = ["Gift", "Dinner", "Samples", "Tour", "Petrol", "Other"]
SALES_EXPENSE_TYPES = [
    "Fuel",
    "Food",
    "Hotel",
    "Travel",
    "Bike Service",
    "Mobile Recharge",
    "Other",
]
COMPANY_EXPENSE_TYPES = [
    "Salary",
    "Samples",
    "Tour",
    "Other Operational",
]
PAYMENT_MODES = ["Cash", "Cheque", "NEFT", "RTGS", "UPI", "Other"]
