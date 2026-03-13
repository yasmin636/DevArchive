from django.urls import path
from django.views.generic import RedirectView
from django.contrib.auth.views import LogoutView

from . import views

urlpatterns = [
    path("", views.accueil, name="accueil"),  # page d'accueil : /
    path("inscription/", views.inscription, name="inscription"),
    path("connexion/", views.ConnexionView.as_view(), name="connexion"),
    # Ancienne URL /profil/ → redirection vers /personnel/profil/
    path("profil/", RedirectView.as_view(pattern_name="profil", permanent=True)),
    path("personnel/", views.PersonnelView.as_view(), name="personnel"),
    path("personnel/profil/", views.profil, name="profil"),
    path("personnel/parametres/", views.parametres_compte, name="parametres_compte"),
    path("personnel/archiver/", views.creer_archive, name="creer_archive"),
    path(
        "personnel/archive/<int:pk>/pdf/",
        views.voir_archive_pdf,
        name="voir_archive_pdf",
    ),
    path(
        "personnel/archive/<int:pk>/modifier/",
        views.modifier_archive,
        name="modifier_archive",
    ),
    path(
        "personnel/archive/<int:pk>/supprimer/",
        views.supprimer_archive,
        name="supprimer_archive",
    ),
    # utilisé dans le template personnel.html : {% url 'logout' %}
    path("deconnexion/", LogoutView.as_view(next_page="connexion"), name="logout"),
]