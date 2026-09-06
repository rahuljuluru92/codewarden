from db.models.orm import InventoryRecord


class InventoryService:
    def check_stock(self, sku: str) -> int:
        record = InventoryRecord.get(sku)
        return record.quantity if record else 0
