from django.urls import path
from django.views.generic import RedirectView
from django.contrib.auth.views import (
    LogoutView,
    PasswordResetView,
    PasswordResetDoneView,
    PasswordResetConfirmView,
    PasswordResetCompleteView,
)

from . import views

urlpatterns = [
    path("", views.accueil, name="accueil"),  # page d'accueil : /
    path("inscription/", views.inscription, name="inscription"),
    path(
        "inscription/confirmation/<uidb64>/<token>/",
        views.confirmer_email,
        name="confirmer_email",
    ),
    path("connexion/", views.ConnexionView.as_view(), name="connexion"),
    # Ancienne URL /etudiant/ → redirection vers le nouvel espace étudiant
    path("etudiant/", RedirectView.as_view(pattern_name="espace_etudiant", permanent=False)),
    # Ancienne URL /profil/ → redirection vers /personnel/profil/
    path("profil/", RedirectView.as_view(pattern_name="profil", permanent=True)),
    path("personnel/", views.PersonnelView.as_view(), name="personnel"),
    path("espace-etudiant/", views.EspaceEtudiantView.as_view(), name="espace_etudiant"),
    path(
        "espace-etudiant/archive/<int:pk>/pdf/",
        views.voir_archive_pdf_etudiant,
        name="voir_archive_pdf_etudiant",
    ),
    path(
        "espace-etudiant/archive/<int:pk>/corrige/pdf/",
        views.voir_corrige_pdf_etudiant,
        name="voir_corrige_pdf_etudiant",
    ),
    path(
        "espace-etudiant/archive/<int:pk>/corrige/telecharger/",
        views.telecharger_corrige_etudiant,
        name="telecharger_corrige_etudiant",
    ),
    path(
        "espace-etudiant/archive/<int:pk>/telecharger/",
        views.telecharger_archive_etudiant,
        name="telecharger_archive_etudiant",
    ),
    path(
        "espace-etudiant/archive/<int:pk>/noter/",
        views.noter_archive_etudiant,
        name="noter_archive_etudiant",
    ),
    path(
        "espace-etudiant/collection/",
        views.etudiant_collection_list,
        name="etudiant_collection",
    ),
    path(
        "espace-etudiant/collection/<int:pk>/",
        views.etudiant_collection_detail,
        name="etudiant_collection_detail",
    ),
    path(
        "espace-etudiant/collection/<int:pk>/archiver/<int:archive_pk>/ajouter/",
        views.etudiant_collection_ajouter_archive,
        name="etudiant_collection_ajouter_archive",
    ),
    path(
        "espace-etudiant/collection/<int:pk>/archiver/<int:archive_pk>/retirer/",
        views.etudiant_collection_retirer_archive,
        name="etudiant_collection_retirer_archive",
    ),
    path(
        "espace-etudiant/collection/<int:pk>/supprimer/",
        views.etudiant_collection_supprimer,
        name="etudiant_collection_supprimer",
    ),
    path(
        "espace-etudiant/favoris/",
        views.etudiant_favoris,
        name="etudiant_favoris",
    ),
    path(
        "espace-etudiant/favori/examen/<int:examen_id>/retirer/",
        views.retirer_favori_etudiant,
        name="retirer_favori_etudiant",
    ),
    path(
        "espace-etudiant/mon-profil/",
        views.etudiant_gerer_profil,
        name="etudiant_profil",
    ),
    path(
        "espace-etudiant/telechargements/",
        views.etudiant_telechargements,
        name="etudiant_telechargements",
    ),
    path(
        "espace-etudiant/archive/<int:pk>/favori/",
        views.toggle_favori_etudiant,
        name="toggle_favori_etudiant",
    ),
    path(
        "espace-etudiant/archive/<int:pk>/commentaires/",
        views.etudiant_commenter_archive,
        name="etudiant_commenter_archive",
    ),
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
    # Tableau de bord admin Sigaud (staff/superuser)
    path("admin-dashboard/", views.admin_dashboard, name="admin_dashboard"),
    path("admin-dashboard/utilisateurs/", views.admin_utilisateurs, name="admin_utilisateurs"),
    path("admin-dashboard/documents/", views.admin_documents, name="admin_documents"),
    path("admin-dashboard/statistiques/", views.admin_statistiques, name="admin_statistiques"),
    path("admin-dashboard/facultes/", views.admin_facultes, name="admin_facultes"),
    path("admin-dashboard/parametres/", views.admin_parametres, name="admin_parametres"),
    path(
        "admin-dashboard/administration-systeme/",
        views.administration_systeme,
        name="administration_systeme",
    ),
    path("admin-dashboard/audit-logs/", views.admin_audit_logs, name="admin_audit_logs"),
    path("admin-dashboard/notifications/", views.admin_notifications, name="admin_notifications"),
    # utilisé dans le template personnel.html : {% url 'logout' %}
    path("deconnexion/", LogoutView.as_view(next_page="connexion"), name="logout"),
    # Mot de passe oublié / réinitialisation
    path(
        "mot-de-passe/oublie/",
        PasswordResetView.as_view(
            template_name="password_reset.html",
            email_template_name="password_reset_email.txt",
            subject_template_name="password_reset_subject.txt",
        ),
        name="password_reset",
    ),
    path(
        "mot-de-passe/oublie/envoye/",
        PasswordResetDoneView.as_view(
            template_name="password_reset_done.html",
        ),
        name="password_reset_done",
    ),
    path(
        "mot-de-passe/reinitialiser/<uidb64>/<token>/",
        PasswordResetConfirmView.as_view(
            template_name="password_reset_confirm.html",
        ),
        name="password_reset_confirm",
    ),
    path(
        "mot-de-passe/reinitialiser/termine/",
        PasswordResetCompleteView.as_view(
            template_name="password_reset_complete.html",
        ),
        name="password_reset_complete",
    ),
]