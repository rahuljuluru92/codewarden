from controllers.report_controller import ReportController


class PricingService:
    def __init__(self):
        # deliberately-planted violation: a service reaching back into the
        # controller layer, creating a circular dependency.
        self.report_controller = ReportController(None)

    def calculate_price(self, base_price: float, quantity: int) -> float:
        return round(base_price * quantity, 2)
