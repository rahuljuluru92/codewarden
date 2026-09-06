"""Example controller module used as a Stage 2 parsing fixture."""
import json
from typing import Optional

from services.user_service import UserService
from db.models.orm import UserRecord as UserRow


class UserController:
    def __init__(self, service: UserService):
        self.service = service

    def get_user(self, user_id: str) -> Optional[dict]:
        user = self.service.find_by_id(user_id)
        if user is None:
            return None
        return json.loads(user.to_json())

    def create_user(self, payload: dict) -> dict:
        return self.service.create(payload)


def health_check() -> dict:
    return {"status": "ok"}
