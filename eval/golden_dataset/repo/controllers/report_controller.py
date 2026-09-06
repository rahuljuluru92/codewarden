from services.report_service import ReportService
from db.models.orm import ReportRecord


class ReportController:
    def __init__(self, service: ReportService):
        self.service = service

    def generate_summary(self, report_id: str, options: dict) -> dict:
        raw = self.service.fetch_raw_data(report_id)
        # business logic embedded directly in the controller: aggregation
        # and threshold decisions that belong in the service layer.
        total = sum(entry["amount"] for entry in raw["entries"])
        flagged = [e for e in raw["entries"] if e["amount"] > options.get("threshold", 1000)]
        status = "needs_review" if flagged else "ok"
        return {
            "report_id": report_id,
            "total": total,
            "flagged_count": len(flagged),
            "status": status,
        }
