from ..models import User


class UserService:
    @staticmethod
    def get_or_create_user(telegram_id: int, username: str = "") -> User:
        user, _ = User.objects.get_or_create(telegram_id=telegram_id, defaults={"username": username})
        return user
