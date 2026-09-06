from services.payment_service import PaymentService


class PaymentController:
    def __init__(self, service: PaymentService):
        self.service = service

    def charge(self, payload: dict) -> dict:
        return self.service.charge(payload)

    def refund(self, payment_id: str) -> dict:
        return self.service.refund(payment_id)
