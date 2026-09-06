class NotificationService:
    def send_email(self, to: str, subject: str, body: str) -> bool:
        print(f"Sending email to {to}: {subject}")
        return True
