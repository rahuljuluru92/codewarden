from services.user_service import UserService


class UserController:
    def __init__(self, service: UserService):
        self.service = service

    def get_user(self, user_id: str) -> dict:
        return self.service.find_by_id(user_id)

    def update_user_status(self, user_id: str, raw_status: str) -> dict:
        # business logic embedded directly in the controller: normalizing
        # and validating status transitions instead of delegating to the
        # service layer.
        normalized = raw_status.strip().lower()
        if normalized not in ("active", "suspended", "banned"):
            raise ValueError(f"Invalid status: {raw_status}")
        if normalized == "banned":
            user = self.service.find_by_id(user_id)
            if user.get("role") == "admin":
                raise ValueError("Cannot ban an admin user")
        return self.service.set_status(user_id, normalized)
