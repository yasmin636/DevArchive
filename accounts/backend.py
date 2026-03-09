"""
Connexion par email OU par username (insensible à la casse).
Nécessaire pour que le personnel créé dans l'admin puisse se connecter avec son email.
"""
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

User = get_user_model()


class EmailOuUsernameBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        if not username or not password:
            return None
        login = username.strip()
        if not login:
            return None

        user = None
        if "@" in login:
            user = User.objects.filter(email__iexact=login).first()
        if user is None:
            user = User.objects.filter(username__iexact=login).first()

        if user and user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None