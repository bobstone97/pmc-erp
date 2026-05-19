# PMC ERP – Pharmaceutical Secondary Sales, Incentive & Recovery Management

Complete pharmaceutical ERP for secondary sales, doctor incentives, stock verification, medical collections, field expenses, and profitability tracking.

## Tech Stack

- Python, Streamlit, PostgreSQL, Pandas, SQLAlchemy, Plotly, ReportLab

## Features

| Module | Description |
|--------|-------------|
| Login & Users | Admin/manager/sales roles, page permissions, password reset |
| Sales Upload | Excel supply upload with duplicate bill prevention |
| Masters | Products, doctors, medicals, areas |
| Product Mapping | Doctor–medical–product with UPSERT |
| Stock Entry | Visit-based verification: Sold = Opening + Supply − Current |
| Commission Engine | SUPPLY, MRP_PERCENT, PAYMENT, TRADE, FIXED |
| Expenses | Doctor (optional commission deduction), sales person, company |
| Payments | Doctor payments with PDF receipts |
| Collections | Medical store payment tracking |
| Medical Ledger | Sales/collection/outstanding (no doctor data) |
| Doctor PNL | Commission, expenses, payments, balance (PDF/Excel) |
| Company PNL | Revenue, expenses, net profit (PDF/Excel) |
| Dashboard | KPIs, charts, top lists |
| Exports | Outstanding, sales, expense Excel reports |

## Setup

### 1. PostgreSQL

Create database:

```sql
CREATE DATABASE pmc_erp;
```

### 2. Environment

```bash
copy .env.example .env
```

Edit `.env`:

```
DATABASE_URL=postgresql://postgres:yourpassword@localhost:5432/pmc_erp
```

### 3. Install dependencies

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 4. Initialize database

```bash
python init_db.py
```

Creates tables and default admin: **admin** / **admin123**

### 5. Run application

```bash
streamlit run app.py
```

Open http://localhost:8501

## Sales Upload Excel Format

Supports billing software exports (e.g. Party Name, Item Name, Date, Bill No#):

| Your Excel column | Required |
|-------------------|----------|
| Party Name / Medical Store | Yes |
| Item Name / Product | Yes |
| Date / Bill Date | Yes |
| Qty | Yes |
| Rate | No |
| **MRP** | Recommended (commission ke liye) |
| Bill No# / Bill No | No |
| Cost / PTS | No |

Ignored columns: Expiry Date, Batch, Month, Scheme, Disc, Free Qty

## Business Rules

1. **Sales upload** = company-to-medical supply (not patient sales)
2. **Secondary sales** estimated via visit stock: `Sold = Opening + Supply − Current`
3. Current stock cannot exceed opening + supply
4. Visit cycles do not overlap (visit date must be after previous visit)
5. Duplicate bills blocked on medical + product + bill_no + bill_date
6. Doctor expenses may deduct from commission (checkbox)
7. Medical ledger never shows doctor/commission data

## Project Structure

```
├── app.py                 # Login & home
├── init_db.py             # DB init + seed admin
├── config.py
├── database/
│   ├── models.py
│   └── connection.py
├── services/              # Business logic
├── pages/                 # Streamlit modules
├── components/
└── utils/
```

## Roles

- **admin** – Full access, user management
- **manager** – All operational modules
- **sales** – Stock entry, expenses, collections, dashboard (view)

Permissions are configurable per user in User Management.
