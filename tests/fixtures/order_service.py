"""Example service module with real business logic, used as a retrieval fixture."""


class OrderService:
    def calculate_total(self, items: list[dict], discount_pct: float = 0.0) -> float:
        subtotal = sum(item["price"] * item["quantity"] for item in items)
        discount = subtotal * (discount_pct / 100)
        total = subtotal - discount
        if total < 0:
            raise ValueError("Total cannot be negative after discount")
        return round(total, 2)

    def apply_loyalty_discount(self, total: float, loyalty_tier: str) -> float:
        tier_discounts = {"gold": 0.1, "silver": 0.05, "bronze": 0.0}
        rate = tier_discounts.get(loyalty_tier, 0.0)
        return round(total * (1 - rate), 2)
