"""Standard profit calculation: sales = sold_qty × rate, cost = sold_qty × cost, profit = sales − cost."""


def line_amounts(sold_qty: float, rate: float, cost: float) -> tuple[float, float, float]:
    sales_amount = float(sold_qty) * float(rate)
    cost_amount = float(sold_qty) * float(cost)
    profit = sales_amount - cost_amount
    return sales_amount, cost_amount, profit
