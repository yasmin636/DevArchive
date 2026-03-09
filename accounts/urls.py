from django.urls import path

from . import views

urlpatterns = [
    path("", views.accueil, name="accueil"),  # page d'accueil : /
    path("inscription/", views.inscription, name="inscription"),
    path("connexion/", views.ConnexionView.as_view(), name="connexion"),
]