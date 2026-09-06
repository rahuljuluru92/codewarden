from services.order_service import OrderService
from db.models.orm import OrderRecord


class OrderController:
    def __init__(self, service: OrderService):
        self.service = service

    def get_order(self, order_id: str) -> dict:
        return self.service.find_by_id(order_id)

    def create_order(self, payload: dict) -> dict:
        return self.service.create(payload)

    def cancel_order(self, order_id: str) -> dict:
        return self.service.cancel(order_id)
