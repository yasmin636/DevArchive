from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import LoginView, LogoutView
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import TemplateView

from .forms import (
    ArchiveForm,
    ConnexionForm,
    EmailChangeForm,
    EtudiantRegistrationForm,
    PasswordChangeFormStyled,
)
from .models import Archive, AssistantPedagogique, Filiere, Niveau

GROUPE_ETUDIANT = "Étudiant"
GROUPE_ASSISTANT = "Assistant pédagogique"
GROUPE_ADMIN_SYSTEME = "Administrateur système"


def user_est_assistant(user):
    """
    True si l'utilisateur est superuser/staff OU appartient au groupe Assistant pédagogique
    OU Administrateur système.
    """
    if not user.is_authenticated:
        return False
    if user.is_superuser or user.is_staff:
        return True
    return user.groups.filter(name__in=[GROUPE_ASSISTANT, GROUPE_ADMIN_SYSTEME]).exists()


class PersonnelRequiredMixin(UserPassesTestMixin):
    """
    Mixin qui restreint l'accès à l'espace personnel aux assistants pédagogiques
    (et admins système via staff/superuser ou groupe).
    """
    login_url = "connexion"

    def test_func(self):
        return user_est_assistant(self.request.user)


def accueil(request):
    """
    Page d'accueil publique de DevArchive.
    """
    return render(request, "accueil.html")


def inscription(request):
    """
    Affiche et traite le formulaire d'inscription étudiant.
    Filière et Niveau sont filtrés par la faculté choisie (côté JS + validation serveur).
    """

    selected_filiere_id = None
    selected_niveau_id = None

    if request.method == "POST":
        form = EtudiantRegistrationForm(request.POST)
        try:
            selected_filiere_id = int(request.POST.get("filiere") or 0) or None
        except (TypeError, ValueError):
            selected_filiere_id = None
        try:
            selected_niveau_id = int(request.POST.get("niveau") or 0) or None
        except (TypeError, ValueError):
            selected_niveau_id = None
        if form.is_valid():
            form.save()
            messages.success(
                request,
                "Votre compte a été créé. Vous pouvez maintenant vous connecter.",
            )
            return redirect("connexion")
    else:
        form = EtudiantRegistrationForm()

    filieres_list = list(
        Filiere.objects.order_by("libelle").values("id", "libelle", "faculte_id")
    )
    niveaux_list = list(
        Niveau.objects.order_by("libelle").values("id", "libelle", "faculte_id")
    )

    return render(
        request,
        "inscription.html",
        {
            "form": form,
            "filieres_list": filieres_list,
            "niveaux_list": niveaux_list,
            "selected_filiere_id": selected_filiere_id,
            "selected_niveau_id": selected_niveau_id,
        },
    )


@login_required
def profil(request):
    """
    Page profil basique pour l'utilisateur connecté.
    Affiche les informations du compte et, si présent, la filière de l'assistant pédagogique.
    """
    assistant = getattr(request.user, "assistant_pedagogique", None)
    return render(
        request,
        "profil.html",
        {
            "assistant": assistant,
        },
    )


@login_required
def parametres_compte(request):
    """
    Page paramètres du compte : changement de mot de passe et d'email.
    """
    from django.contrib.auth import update_session_auth_hash

    assistant = getattr(request.user, "assistant_pedagogique", None)
    password_form = PasswordChangeFormStyled(user=request.user)
    email_form = EmailChangeForm(user=request.user)

    if request.method == "POST":
        if "change_password" in request.POST:
            password_form = PasswordChangeFormStyled(
                user=request.user, data=request.POST
            )
            if password_form.is_valid():
                password_form.save()
                update_session_auth_hash(request, request.user)
                messages.success(request, "Votre mot de passe a été modifié.")
                return redirect("parametres_compte")
            for name in password_form.errors:
                if name in password_form.fields:
                    cls = password_form.fields[name].widget.attrs.get("class", "")
                    if "is-invalid" not in cls:
                        password_form.fields[name].widget.attrs["class"] = (cls + " is-invalid").strip()
        elif "change_email" in request.POST:
            email_form = EmailChangeForm(user=request.user, data=request.POST)
            if email_form.is_valid():
                email_form.save()
                messages.success(request, "Votre adresse email a été mise à jour.")
                return redirect("parametres_compte")
            for name in email_form.errors:
                if name in email_form.fields:
                    cls = email_form.fields[name].widget.attrs.get("class", "")
                    if "is-invalid" not in cls:
                        email_form.fields[name].widget.attrs["class"] = (cls + " is-invalid").strip()

    return render(
        request,
        "parametres.html",
        {
            "assistant": assistant,
            "password_form": password_form,
            "email_form": email_form,
        },
    )


class ConnexionView(LoginView):
    """
    Page de connexion (email + mot de passe).
    Utilise la redirection par groupe après authentification.
    """

    template_name = "Connexion.html"
    authentication_form = ConnexionForm
    redirect_authenticated_user = False  # on veut toujours afficher la page en GET

    def get_success_url(self):
        """
        Priorité :
        1. paramètre ?next=
        2. espace personnel si assistant pédagogique / admin système
        3. sinon page d'inscription (profil étudiant)
        """
        url = self.get_redirect_url()
        if url:
            return url
        if user_est_assistant(self.request.user):
            return reverse_lazy("personnel")
        return reverse_lazy("inscription")


class PersonnelView(PersonnelRequiredMixin, LoginRequiredMixin, TemplateView):
    """
    Espace personnel réservé aux assistants pédagogiques.
    Les données affichées sont filtrées par filière de l'assistant.
    """

    template_name = "personnel.html"
    login_url = "connexion"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        assistant = getattr(self.request.user, "assistant_pedagogique", None)
        archives = _archives_queryset_for_user(self.request).order_by("-date_archive")
        if assistant:
            ctx["assistant_filiere"] = assistant.filiere
        ctx["archive_form"] = ArchiveForm()
        ctx["archives"] = archives
        ctx["stat_total"] = archives.count()
        ctx["stat_cc"] = archives.filter(type="CC").count()
        ctx["stat_exam"] = archives.filter(type="Examen Final").count()
        ctx["stat_annee"] = (
            archives.values_list("annee", flat=True).order_by("-annee").first() or "—"
        )
        return ctx


@login_required
def creer_archive(request):
    if request.method != "POST":
        raise Http404()
    form = ArchiveForm(request.POST, request.FILES)
    if form.is_valid():
        archive = form.save(commit=False)
        archive.created_by = request.user
        assistant = getattr(request.user, "assistant_pedagogique", None)
        if assistant:
            archive.filiere = assistant.filiere.libelle.strip()
        archive.save()
        messages.success(request, "Le document a été archivé avec succès.")
    else:
        # On affiche un message d'erreur lisible pour aider à corriger le formulaire
        msg = "Le formulaire d'archivage contient des erreurs. "
        if form.errors.get("type"):
            msg += "Vous devez sélectionner le type (CC ou Examen Final). "
        messages.error(request, msg)
    return redirect("personnel")


@login_required
def voir_archive_pdf(request, pk: int):
    assistant = getattr(request.user, "assistant_pedagogique", None)
    if not assistant and not (request.user.is_superuser or request.user.is_staff):
        raise Http404()
    qs = Archive.objects.all()
    if assistant:
        qs = qs.filter(filiere__iexact=assistant.filiere.libelle.strip())
    archive = get_object_or_404(qs, pk=pk)
    if not archive.fichier:
        raise Http404("Aucun fichier associé.")
    return FileResponse(archive.fichier.open("rb"), content_type="application/pdf")


def _archives_queryset_for_user(request):
    assistant = getattr(request.user, "assistant_pedagogique", None)
    qs = Archive.objects.all()
    if assistant:
        qs = qs.filter(filiere__iexact=assistant.filiere.libelle.strip())
    return qs


@login_required
def modifier_archive(request, pk: int):
    qs = _archives_queryset_for_user(request)
    archive = get_object_or_404(qs, pk=pk)
    if request.method == "POST":
        form = ArchiveForm(request.POST, request.FILES, instance=archive)
        if form.is_valid():
            form.save()
            messages.success(request, "L'archive a été mise à jour.")
            return redirect("personnel")
    else:
        form = ArchiveForm(instance=archive)
    return render(request, "archive_form.html", {"form": form, "archive": archive})


@login_required
def supprimer_archive(request, pk: int):
    qs = _archives_queryset_for_user(request)
    archive = get_object_or_404(qs, pk=pk)
    archive.delete()
    messages.success(request, "L'archive a été supprimée.")
    return redirect("personnel")