from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login as auth_login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import LoginView
from django.core.cache import cache
from django.core.mail import send_mail
from django.db import DatabaseError, IntegrityError, models
from django.db.models.deletion import ProtectedError, RestrictedError
from django.db.utils import ProgrammingError
from django.db.models import Avg, Count
from django.http import FileResponse, Http404, JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils.decorators import method_decorator
from datetime import timedelta

from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import TemplateView
import random
import logging

from .forms import (
    AdminEditUserForm,
    ArchiveForm,
    ConnexionForm,
    EmailChangeForm,
    EtudiantRegistrationForm,
    FaculteForm,
    FiliereForm,
    PasswordChangeFormStyled,
    ProfilEtudiantForm,
)
from .constants import CORRIGE_GRATUITS_MAX
from .constants import ABONNEMENT_ETUDIANT_PRIX_USD
from .models import (
    AbonnementEtudiant,
    Archive,
    AssistantPedagogique,
    Collection,
    CollectionArchive,
    Commentaire,
    CommentaireArchive,
    Etudiant,
    Faculte,
    Favori,
    FavoriArchive,
    Filiere,
    Historique,
    HistoriqueArchive,
    Niveau,
    NoteArchive,
    ConsultationCorrigeGratuite,
    TelechargementEtudiant,
    PaiementAbonnement,
)
from .services.mastercard_checkout import MastercardCheckoutService

logger = logging.getLogger(__name__)

GROUPE_ETUDIANT = "Étudiant"
GROUPE_ASSISTANT = "Assistant pédagogique"
GROUPE_ADMIN_SYSTEME = "Administrateur système"


def user_est_admin_sigaud(user):
    """
    Accès au tableau de bord admin Sigaeud (/admin-dashboard/) :
    superuser Django, ou membre du groupe « Administrateur système ».

    Le simple « Staff » (personnel administratif) n’ouvre pas cet espace :
    ces comptes vont sur l’espace personnel (personnel.html).
    """
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user.groups.filter(name=GROUPE_ADMIN_SYSTEME).exists()


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


def user_est_etudiant(user):
    """True si l'utilisateur a un profil Étudiant (et pas assistant/admin)."""
    if not user.is_authenticated:
        return False
    if user_est_admin_sigaud(user):
        return False
    return hasattr(user, "etudiant") and user.etudiant is not None


class PersonnelRequiredMixin(UserPassesTestMixin):
    """
    Mixin qui restreint l'accès à l'espace personnel aux assistants pédagogiques
    (et admins système via staff/superuser ou groupe).
    """
    login_url = "connexion_personnel"

    def test_func(self):
        return user_est_assistant(self.request.user)


class EtudiantRequiredMixin(UserPassesTestMixin):
    """Mixin qui restreint l'accès à l'espace étudiant aux utilisateurs avec profil Étudiant."""
    login_url = "connexion_etudiant"

    def test_func(self):
        return user_est_etudiant(self.request.user)

    def handle_no_permission(self):
        # Evite une page 403 brute : on redirige vers l'espace adapte au role.
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        if user_est_admin_sigaud(self.request.user):
            messages.info(self.request, "Votre compte est admin : redirection vers le tableau de bord.")
            return redirect("admin_dashboard")
        if user_est_assistant(self.request.user):
            messages.info(self.request, "Votre compte est personnel : redirection vers l'espace personnel.")
            return redirect("personnel")
        messages.warning(self.request, "Acces etudiant reserve aux comptes avec profil etudiant.")
        return redirect("connexion_etudiant")


def accueil(request):
    """
    Page d'accueil publique de SIGAEUD.
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
            user = form.save()
            # Le compte reste inactif tant que l'email n'est pas confirmé
            user.is_active = False
            user.save(update_fields=["is_active"])

            # Envoi d'un code OTP à 6 chiffres par email
            code = f"{random.randint(0, 999999):06d}"
            expires_at = timezone.now() + timedelta(minutes=15)
            request.session["inscription_verification"] = {
                "user_id": user.pk,
                "email": user.email,
                "code": code,
                "expires_at": expires_at.isoformat(),
            }
            request.session.modified = True

            sujet = "Code de vérification - SIGAEUD"
            message = (
                "Bonjour,\n\n"
                "Vous venez de créer un compte sur SIGAEUD avec cette adresse email.\n"
                "Saisissez ce code de vérification pour activer votre compte :\n\n"
                f"{code}\n\n"
                "Ce code expire dans 15 minutes.\n\n"
                "Si vous n'êtes pas à l'origine de cette inscription, vous pouvez ignorer ce message.\n\n"
                "Cordialement,\n"
                "L'équipe SIGAEUD"
            )
            from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None)
            try:
                send_mail(sujet, message, from_email, [user.email], fail_silently=True)
            except Exception:
                # On ne bloque pas l'inscription en cas de problème SMTP, mais le compte restera inactif
                pass

            messages.success(
                request,
                "Votre compte a été créé. Un email de confirmation vient d'être envoyé. "
                "Saisissez le code à 6 chiffres reçu pour activer votre compte.",
            )
            return redirect("verifier_code_inscription")
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


def verifier_code_inscription(request):
    """
    Active le compte après saisie d'un code de vérification à 6 chiffres.
    """
    payload = request.session.get("inscription_verification")
    if not payload:
        messages.info(request, "Aucune vérification en cours. Merci de vous inscrire.")
        return redirect("inscription")

    email = payload.get("email", "")
    code_input = ""

    if request.method == "POST":
        action = request.POST.get("action", "verify")
        User = get_user_model()
        try:
            user = User.objects.get(pk=payload.get("user_id"))
        except User.DoesNotExist:
            request.session.pop("inscription_verification", None)
            messages.error(request, "Session de vérification invalide. Merci de vous réinscrire.")
            return redirect("inscription")

        if action == "resend":
            new_code = f"{random.randint(0, 999999):06d}"
            expires_at = timezone.now() + timedelta(minutes=15)
            payload.update({"code": new_code, "expires_at": expires_at.isoformat()})
            request.session["inscription_verification"] = payload
            request.session.modified = True

            sujet = "Nouveau code de vérification - SIGAEUD"
            message = (
                "Bonjour,\n\n"
                "Voici votre nouveau code de vérification SIGAEUD :\n\n"
                f"{new_code}\n\n"
                "Ce code expire dans 15 minutes.\n\n"
                "Cordialement,\n"
                "L'équipe SIGAEUD"
            )
            from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None)
            try:
                send_mail(sujet, message, from_email, [user.email], fail_silently=True)
            except Exception:
                pass
            messages.success(request, "Un nouveau code a été envoyé à votre adresse email.")
            return redirect("verifier_code_inscription")

        code_input = (request.POST.get("code") or "").strip()
        expires_at_raw = payload.get("expires_at")
        try:
            expires_at = timezone.datetime.fromisoformat(expires_at_raw)
            if timezone.is_naive(expires_at):
                expires_at = timezone.make_aware(expires_at, timezone.get_current_timezone())
        except Exception:
            expires_at = timezone.now() - timedelta(seconds=1)

        if timezone.now() > expires_at:
            messages.error(request, "Le code a expiré. Demandez un nouveau code.")
        elif code_input != payload.get("code"):
            messages.error(request, "Code invalide. Vérifiez les 6 chiffres saisis.")
        else:
            if not user.is_active:
                user.is_active = True
                user.save(update_fields=["is_active"])
            request.session.pop("inscription_verification", None)
            messages.success(request, "Votre adresse email a été confirmée. Vous pouvez vous connecter.")
            return redirect("connexion_etudiant")

    return render(
        request,
        "verifier_code_inscription.html",
        {"email": email, "code_value": code_input},
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


@method_decorator(ensure_csrf_cookie, name="dispatch")
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
        2. tableau de bord admin : superuser ou groupe « Administrateur système » uniquement
        3. espace personnel (personnel.html) : staff, assistant pédagogique, etc. (via user_est_assistant)
        4. espace étudiant si étudiant
        5. sinon page d'inscription
        """
        url = self.get_redirect_url()
        if url:
            return url
        u = self.request.user
        if user_est_admin_sigaud(u):
            return reverse_lazy("admin_dashboard")
        if user_est_assistant(u):
            return reverse_lazy("personnel")
        if user_est_etudiant(u):
            return reverse_lazy("espace_etudiant")
        return reverse_lazy("inscription")


@method_decorator(ensure_csrf_cookie, name="dispatch")
class ConnexionParRoleView(LoginView):
    """
    Vue de connexion générique restreinte à un rôle.
    """

    template_name = "Connexion.html"
    authentication_form = ConnexionForm
    redirect_authenticated_user = False
    login_space_label = "SIGAEUD"
    show_signup_link = False
    default_success_url_name = "accueil"
    enable_login_attempt_limit = False

    def user_is_allowed(self, user):
        return True

    def _login_attempt_limit_max(self):
        return int(getattr(settings, "LOGIN_ATTEMPT_LIMIT_MAX", 5))

    def _login_attempt_limit_window(self):
        return int(getattr(settings, "LOGIN_ATTEMPT_LIMIT_WINDOW_SECONDS", 900))

    def _client_ip(self):
        forwarded_for = self.request.META.get("HTTP_X_FORWARDED_FOR", "")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        return (self.request.META.get("REMOTE_ADDR") or "unknown").strip()

    def _attempt_cache_key(self):
        scope = self.__class__.__name__
        ip = self._client_ip()
        return f"login_attempts:{scope}:{ip}"

    def _is_locked(self):
        if not self.enable_login_attempt_limit:
            return False
        return int(cache.get(self._attempt_cache_key(), 0) or 0) >= self._login_attempt_limit_max()

    def _record_failed_attempt(self):
        if not self.enable_login_attempt_limit:
            return
        key = self._attempt_cache_key()
        timeout = self._login_attempt_limit_window()
        current = int(cache.get(key, 0) or 0)
        cache.set(key, current + 1, timeout=timeout)

    def _clear_failed_attempts(self):
        if not self.enable_login_attempt_limit:
            return
        cache.delete(self._attempt_cache_key())

    def post(self, request, *args, **kwargs):
        if self._is_locked():
            form = self.get_form()
            wait_minutes = max(1, self._login_attempt_limit_window() // 60)
            form.add_error(
                None,
                f"Trop de tentatives de connexion. Réessayez dans environ {wait_minutes} minute(s).",
            )
            return self.form_invalid(form)
        return super().post(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["login_space_label"] = self.login_space_label
        ctx["show_signup_link"] = self.show_signup_link
        return ctx

    def get_success_url(self):
        url = self.get_redirect_url()
        if url:
            return url
        return reverse_lazy(self.default_success_url_name)

    def form_valid(self, form):
        user = form.get_user()
        if not self.user_is_allowed(user):
            messages.error(
                self.request,
                "Cet espace de connexion n'est pas autorisé pour votre compte.",
            )
            return self.form_invalid(form)
        auth_login(self.request, user)
        self._clear_failed_attempts()
        return redirect(self.get_success_url())

    def form_invalid(self, form):
        if self.request.method == "POST":
            self._record_failed_attempt()
        return super().form_invalid(form)


class ConnexionEtudiantView(ConnexionParRoleView):
    login_space_label = "Espace étudiant"
    show_signup_link = True
    default_success_url_name = "espace_etudiant"

    def user_is_allowed(self, user):
        return user_est_etudiant(user)


class ConnexionPersonnelView(ConnexionParRoleView):
    login_space_label = "Espace assistant"
    show_signup_link = False
    default_success_url_name = "personnel"
    enable_login_attempt_limit = True

    def user_is_allowed(self, user):
        return user_est_assistant(user) and not user_est_admin_sigaud(user)


class ConnexionAdminView(ConnexionParRoleView):
    login_space_label = "Espace administrateur"
    show_signup_link = False
    default_success_url_name = "admin_dashboard"
    enable_login_attempt_limit = True

    def user_is_allowed(self, user):
        return user_est_admin_sigaud(user)


@login_required
def deconnexion(request):
    """
    Déconnecte l'utilisateur puis redirige vers la page de connexion.
    Accepte GET/POST pour éviter les erreurs CSRF en tunnel de dev.
    """
    from django.contrib.auth import logout as auth_logout

    if user_est_admin_sigaud(request.user):
        redirect_url_name = "connexion_admin"
    elif user_est_assistant(request.user):
        redirect_url_name = "connexion_personnel"
    else:
        redirect_url_name = "connexion_etudiant"

    auth_logout(request)
    return redirect(redirect_url_name)


class PersonnelView(PersonnelRequiredMixin, LoginRequiredMixin, TemplateView):
    """
    Espace personnel réservé aux assistants pédagogiques.
    Les données affichées sont filtrées par filière de l'assistant.
    """

    template_name = "personnel.html"
    login_url = "connexion_personnel"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        assistant = getattr(self.request.user, "assistant_pedagogique", None)
        archives = _archives_queryset_for_user(self.request).order_by("-date_archive")
        if assistant:
            ctx["assistant_filiere"] = assistant.filiere
            ctx["niveaux_qs"] = Niveau.objects.filter(
                faculte_id=assistant.filiere.faculte_id
            ).order_by("code", "libelle")
        else:
            ctx["niveaux_qs"] = Niveau.objects.select_related("faculte").order_by(
                "faculte__code", "code"
            )
        ctx["archive_form"] = ArchiveForm()
        ctx["archives"] = archives
        ctx["stat_total"] = archives.count()
        ctx["stat_cc"] = archives.filter(type="CC").count()
        ctx["stat_exam"] = archives.filter(type="Examen Final").count()
        ctx["stat_annee"] = (
            archives.values_list("annee", flat=True).order_by("-annee").first() or "—"
        )
        return ctx


def _archives_queryset_for_etudiant(request):
    """Archives visibles par l'étudiant (sa filière et, si renseigné, son niveau)."""
    etudiant = getattr(request.user, "etudiant", None)
    if not etudiant:
        return Archive.objects.none()
    qs = Archive.objects.filter(
        filiere__iexact=etudiant.filiere.libelle.strip()
    )
    # Si l'archive a un niveau renseigné, on ne montre que celles du niveau de l'étudiant.
    return qs.filter(
        models.Q(niveau__isnull=True) | models.Q(niveau=etudiant.niveau)
    ).order_by("-date_archive")


def _enrich_sujets_cards(archives_list, user):
    """Métadonnées pour les cartes « sujets visités » : favoris, moyenne des notes."""
    out = []
    for a in archives_list:
        if a.examen_id:
            fav_count = Favori.objects.filter(examen_id=a.examen_id).count()
        else:
            fav_count = FavoriArchive.objects.filter(archive_id=a.pk).count()
        agg = NoteArchive.objects.filter(archive=a).aggregate(avg=Avg("note"), n=Count("id"))
        avg = agg["avg"]
        n_note = agg["n"] or 0
        user_note = (
            NoteArchive.objects.filter(archive=a, user=user)
            .values_list("note", flat=True)
            .first()
        )
        out.append(
            {
                "archive": a,
                "favori_count": fav_count,
                "note_moyenne": round(float(avg), 1) if avg is not None else None,
                "nb_notes": n_note,
                "user_note": user_note,
            }
        )
    return out


class EspaceEtudiantView(EtudiantRequiredMixin, LoginRequiredMixin, TemplateView):
    """
    Tableau de bord étudiant : sujets de sa filière, recherche, historique.
    """
    template_name = "etudiant.html"
    login_url = "connexion_etudiant"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        etudiant = self.request.user.etudiant
        ctx["etudiant"] = etudiant
        ctx["faculte"] = etudiant.filiere.faculte
        archives = _archives_queryset_for_etudiant(self.request)
        matieres_list = list(
            archives.values_list("module", flat=True)
            .distinct()
            .order_by("module")
        )
        matieres_list = [m for m in matieres_list if m and m.strip()]
        matiere_choisie = (self.request.GET.get("matiere") or "").strip()
        if matiere_choisie:
            archives = archives.filter(module__iexact=matiere_choisie)
        ctx["matieres_list"] = matieres_list
        ctx["matiere_choisie"] = matiere_choisie
        ctx["archives"] = archives
        top = list(archives[:8])
        ctx["sujets_plus_visites"] = top
        ctx["sujets_cartes"] = _enrich_sujets_cards(top, self.request.user)
        archive_by_examen = {}
        for a in archives:
            if a.examen_id and a.examen_id not in archive_by_examen:
                archive_by_examen[a.examen_id] = a
        # Historique par examen
        items = []
        for h in Historique.objects.filter(user=self.request.user).select_related("examen").order_by("-date_vue"):
            arch = archive_by_examen.get(h.examen_id)
            items.append({"date_vue": h.date_vue, "titre": h.examen.titre, "archive": arch})
        # Historique par archive (sans examen)
        try:
            for ha in HistoriqueArchive.objects.filter(user=self.request.user).select_related("archive").order_by("-date_vue"):
                if ha.archive_id in set(archives.values_list("id", flat=True)):
                    items.append({"date_vue": ha.date_vue, "titre": ha.archive.title, "archive": ha.archive})
        except ProgrammingError:
            pass
        items.sort(key=lambda x: x["date_vue"], reverse=True)
        ctx["historiques"] = items[:10]
        favori_examen_ids = set(
            Favori.objects.filter(user=self.request.user).values_list("examen_id", flat=True)
        )
        try:
            favori_archive_ids = set(
                FavoriArchive.objects.filter(user=self.request.user).values_list("archive_id", flat=True)
            )
        except ProgrammingError:
            favori_archive_ids = set()
        ctx["favori_examen_ids"] = favori_examen_ids
        ctx["favori_archive_ids"] = favori_archive_ids
        ctx.update(_context_quota_corrige(self.request.user, archives))
        return ctx


class EtudiantPlaceholderView(EtudiantRequiredMixin, LoginRequiredMixin, TemplateView):
    """Vue générique pour les pages étudiant (favoris, profil, téléchargements)."""
    template_name = "etudiant_placeholder.html"
    page_title = "Espace étudiant"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["etudiant"] = self.request.user.etudiant
        ctx["faculte"] = ctx["etudiant"].filiere.faculte
        ctx["page_title"] = self.page_title
        return ctx


@login_required
def etudiant_favoris(request):
    """Page « Mes favoris » : liste des examens et archives mis en favori."""
    if not user_est_etudiant(request.user):
        raise Http404()
    etudiant = request.user.etudiant
    archives = _archives_queryset_for_etudiant(request)
    archive_by_examen = {}
    for a in archives:
        if a.examen_id and a.examen_id not in archive_by_examen:
            archive_by_examen[a.examen_id] = a
    # Favoris par examen (examen.titre + archive si dispo)
    items = []
    for f in Favori.objects.filter(user=request.user).select_related("examen").order_by("-date_ajout"):
        arch = archive_by_examen.get(f.examen_id)
        items.append({"type": "examen", "date_ajout": f.date_ajout, "favori": f, "archive": arch, "titre": f.examen.titre})
    # Favoris par archive directe (sans examen)
    try:
        for fa in FavoriArchive.objects.filter(user=request.user).select_related("archive").order_by("-date_ajout"):
            if fa.archive_id in set(archives.values_list("id", flat=True)):
                items.append({"type": "archive", "date_ajout": fa.date_ajout, "favori_archive": fa, "archive": fa.archive, "titre": fa.archive.title})
    except ProgrammingError:
        pass
    items.sort(key=lambda x: x["date_ajout"], reverse=True)
    ctx = {
        "etudiant": etudiant,
        "faculte": etudiant.filiere.faculte,
        "favoris": items,
    }
    ctx.update(_context_quota_corrige(request.user, archives))
    return render(request, "etudiant_favoris.html", ctx)


@login_required
def etudiant_collection_list(request):
    """Liste des collections de l'étudiant et formulaire de création."""
    if not user_est_etudiant(request.user):
        raise Http404()
    etudiant = request.user.etudiant
    if request.method == "POST" and request.POST.get("creer_collection"):
        nom = (request.POST.get("nom") or "").strip()
        if nom:
            Collection.objects.create(user=request.user, nom=nom)
            messages.success(request, f"Collection « {nom} » créée.")
            return redirect("etudiant_collection")
        messages.error(request, "Indiquez un nom pour la collection.")
    collections = Collection.objects.filter(user=request.user).prefetch_related(
        "archives_collection"
    ).order_by("-date_creation")
    return render(
        request,
        "etudiant_collection_list.html",
        {"etudiant": etudiant, "collections": collections},
    )


@login_required
def etudiant_collection_detail(request, pk: int):
    """Détail d'une collection : archives contenues, ajouter via recherche (matière + filtres)."""
    if not user_est_etudiant(request.user):
        raise Http404()
    collection = get_object_or_404(Collection, pk=pk, user=request.user)
    archives = _archives_queryset_for_etudiant(request)
    archive_ids_in_collection = set(
        collection.archives_collection.values_list("archive_id", flat=True)
    )
    archives_in_collection = [
        (ca.archive, ca) for ca in collection.archives_collection.select_related("archive").order_by("-date_ajout")
    ]
    # Archives qu'on peut encore ajouter (hors collection)
    archives_disponibles_qs = archives.exclude(pk__in=archive_ids_in_collection)
    matieres_list = list(
        archives_disponibles_qs.values_list("module", flat=True).distinct().order_by("module")
    )
    matieres_list = [m for m in matieres_list if m and m.strip()]
    matiere_choisie = (request.GET.get("matiere") or "").strip()
    if matiere_choisie:
        archives_disponibles_qs = archives_disponibles_qs.filter(module__iexact=matiere_choisie)
    archives_disponibles = list(archives_disponibles_qs)
    ctx = {
        "collection": collection,
        "archives_in_collection": archives_in_collection,
        "archives_disponibles": archives_disponibles,
        "matieres_list": matieres_list,
        "matiere_choisie": matiere_choisie,
    }
    ctx.update(_context_quota_corrige(request.user, archives))
    return render(request, "etudiant_collection_detail.html", ctx)


@login_required
def etudiant_collection_ajouter_archive(request, pk: int, archive_pk: int):
    """Ajoute une archive à une collection."""
    if not user_est_etudiant(request.user):
        raise Http404()
    collection = get_object_or_404(Collection, pk=pk, user=request.user)
    qs = _archives_queryset_for_etudiant(request)
    archive = get_object_or_404(qs, pk=archive_pk)
    CollectionArchive.objects.get_or_create(collection=collection, archive=archive)
    messages.success(request, "Sujet ajouté à la collection.")
    return redirect("etudiant_collection_detail", pk=pk)


@login_required
def etudiant_collection_retirer_archive(request, pk: int, archive_pk: int):
    """Retire une archive d'une collection."""
    if not user_est_etudiant(request.user):
        raise Http404()
    collection = get_object_or_404(Collection, pk=pk, user=request.user)
    CollectionArchive.objects.filter(collection=collection, archive_id=archive_pk).delete()
    messages.success(request, "Sujet retiré de la collection.")
    return redirect("etudiant_collection_detail", pk=pk)


@login_required
def etudiant_collection_supprimer(request, pk: int):
    """Supprime une collection."""
    if not user_est_etudiant(request.user):
        raise Http404()
    if request.method != "POST":
        return redirect("etudiant_collection")
    collection = get_object_or_404(Collection, pk=pk, user=request.user)
    nom = collection.nom
    collection.delete()
    messages.success(request, f"Collection « {nom} » supprimée.")
    return redirect("etudiant_collection")


@login_required
def etudiant_gerer_profil(request):
    """Page « Gérer mon profil » : photo, nom, email, mot de passe, filière, niveau."""
    if not user_est_etudiant(request.user):
        raise Http404()
    etudiant = request.user.etudiant
    ctx = {"etudiant": etudiant}

    # Formulaire profil (identité, filière, niveau, photo)
    if request.method == "POST" and "enregistrer_profil" in request.POST:
        form_profil = ProfilEtudiantForm(
            request.user,
            request.POST,
            request.FILES,
        )
        if form_profil.is_valid():
            form_profil.save()
            messages.success(request, "Profil mis à jour. Votre tableau de bord reflète vos nouvelles informations.")
            return redirect("espace_etudiant")
    else:
        form_profil = ProfilEtudiantForm(request.user)

    # Formulaire mot de passe
    if request.method == "POST" and "changer_mot_de_passe" in request.POST:
        form_mdp = PasswordChangeFormStyled(user=request.user, data=request.POST)
        if form_mdp.is_valid():
            form_mdp.save()
            from django.contrib.auth import update_session_auth_hash
            update_session_auth_hash(request, form_mdp.user)
            messages.success(request, "Mot de passe modifié.")
            return redirect("etudiant_profil")
    else:
        form_mdp = PasswordChangeFormStyled(user=request.user)

    import json
    filieres_par_faculte = {}
    niveaux_par_faculte = {}
    for fac in Faculte.objects.all().order_by("libelle"):
        filieres_par_faculte[str(fac.id)] = [
            {"id": f.id, "libelle": f.libelle}
            for f in Filiere.objects.filter(faculte=fac).order_by("libelle")
        ]
        niveaux_par_faculte[str(fac.id)] = [
            {"id": n.id, "libelle": n.libelle}
            for n in Niveau.objects.filter(faculte=fac).order_by("libelle")
        ]
    ctx["form_profil"] = form_profil
    ctx["form_mdp"] = form_mdp
    ctx["filieres_par_faculte"] = json.dumps(filieres_par_faculte)
    ctx["niveaux_par_faculte"] = json.dumps(niveaux_par_faculte)
    return render(request, "etudiant_profil.html", ctx)


@login_required
def etudiant_telechargements(request):
    """Page « Historique des téléchargements » : liste des archives téléchargées par l'étudiant."""
    if not user_est_etudiant(request.user):
        raise Http404()
    etudiant = request.user.etudiant
    items = (
        TelechargementEtudiant.objects.filter(user=request.user)
        .select_related("archive")
        .order_by("-date_telechargement")
    )
    return render(
        request,
        "etudiant_telechargements.html",
        {"etudiant": etudiant, "telechargements": items},
    )


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
        msg_ok = "Le document a été archivé avec succès."
        if archive.fichier_corrige:
            msg_ok += (
                " Le corrigé est joint : les étudiants pourront l’ouvrir avec « Consulter correction » "
                "après avoir consulté le sujet."
            )
        messages.success(request, msg_ok)
    else:
        msg = "Le formulaire d'archivage contient des erreurs. "
        if form.errors.get("type"):
            msg += "Vous devez sélectionner le type (CC ou Examen Final). "
        err_parts = []
        for field, errs in form.errors.items():
            err_parts.append(f"{field}: {errs.as_text().strip()}")
        if err_parts:
            msg += " " + " ".join(err_parts)
        messages.error(request, msg)
    return redirect("personnel")


@login_required
def voir_archive_pdf(request, pk: int):
    assistant = getattr(request.user, "assistant_pedagogique", None)
    is_admin_sigaud = user_est_admin_sigaud(request.user)
    if not assistant and not is_admin_sigaud and not (
        request.user.is_superuser or request.user.is_staff
    ):
        raise Http404()
    qs = Archive.objects.all()
    if assistant:
        qs = qs.filter(filiere__iexact=assistant.filiere.libelle.strip())
    archive = get_object_or_404(qs, pk=pk)
    if not archive.fichier:
        raise Http404("Aucun fichier associé.")
    return FileResponse(archive.fichier.open("rb"), content_type="application/pdf")


@login_required
def voir_archive_pdf_etudiant(request, pk: int):
    """Permet à un étudiant de consulter le PDF dans le navigateur. nb_vues n'est incrémenté qu'une seule fois par utilisateur (première consultation)."""
    if not user_est_etudiant(request.user):
        raise Http404()
    qs = _archives_queryset_for_etudiant(request)
    archive = get_object_or_404(qs, pk=pk)
    if not archive.fichier:
        raise Http404("Aucun fichier associé.")
    if not archive.fichier.storage.exists(archive.fichier.name):
        messages.error(request, "Le fichier PDF demandé est introuvable.")
        return redirect("espace_etudiant")
    premiere_consultation = False
    if archive.examen_id:
        obj, created = Historique.objects.get_or_create(
            user=request.user,
            examen_id=archive.examen_id,
            defaults={},
        )
        premiere_consultation = created
        obj.date_vue = timezone.now()
        obj.save(update_fields=["date_vue"])
    else:
        try:
            obj, created = HistoriqueArchive.objects.get_or_create(
                user=request.user,
                archive=archive,
                defaults={},
            )
            premiere_consultation = created
            obj.date_vue = timezone.now()
            obj.save(update_fields=["date_vue"])
        except ProgrammingError:
            pass
    if premiere_consultation:
        archive.nb_vues += 1
        archive.save(update_fields=["nb_vues"])
    response = FileResponse(archive.fichier.open("rb"), content_type="application/pdf")
    response["Content-Disposition"] = "inline; filename*=UTF-8''" + _safe_filename(archive)
    return response


@login_required
def consulter_corrige_etudiant(request, pk: int):
    """Affiche le corrigé dans une page interne SIGAEUD (sans téléchargement étudiant)."""
    if not user_est_etudiant(request.user):
        raise Http404()
    qs = _archives_queryset_for_etudiant(request)
    archive = get_object_or_404(qs, pk=pk)
    if not archive.fichier_corrige:
        raise Http404("Aucun corrigé associé.")
    denied = _reserver_accès_corrige_gratuit(request, archive)
    if denied is not None:
        return denied
    request.session["corrige_embed_allowed_pk"] = archive.pk
    request.session.modified = True
    return render(
        request,
        "etudiant_corrige_consultation.html",
        {"archive": archive, "etudiant": request.user.etudiant},
    )


@login_required
def voir_corrige_pdf_etudiant(request, pk: int):
    """Consultation du corrigé PDF (sans incrémenter les vues du sujet)."""
    if not user_est_etudiant(request.user):
        raise Http404()
    qs = _archives_queryset_for_etudiant(request)
    archive = get_object_or_404(qs, pk=pk)
    if not archive.fichier_corrige:
        raise Http404("Aucun corrigé associé.")
    allowed_pk = request.session.get("corrige_embed_allowed_pk")
    if allowed_pk != archive.pk:
        messages.info(
            request,
            "Veuillez ouvrir le corrigé depuis la page de consultation interne.",
        )
        return redirect("consulter_corrige_etudiant", pk=archive.pk)
    denied = _reserver_accès_corrige_gratuit(request, archive)
    if denied is not None:
        return denied
    response = FileResponse(archive.fichier_corrige.open("rb"), content_type="application/pdf")
    response["Content-Disposition"] = "inline; filename*=UTF-8''" + _safe_filename_corrige(archive)
    return response


@login_required
def telecharger_corrige_etudiant(request, pk: int):
    """Le téléchargement des corrigés est désactivé côté étudiant."""
    messages.warning(
        request,
        "Le téléchargement du corrigé n'est pas autorisé. Consultation uniquement dans l'espace étudiant.",
    )
    return redirect("consulter_corrige_etudiant", pk=pk)


@login_required
@require_POST
def noter_archive_etudiant(request, pk: int):
    """Enregistre une note 1–5 sur une archive (AJAX JSON)."""
    if not user_est_etudiant(request.user):
        return JsonResponse({"ok": False, "error": "forbidden"}, status=403)
    try:
        note = int(request.POST.get("note") or 0)
    except (TypeError, ValueError):
        return JsonResponse({"ok": False, "error": "invalid"}, status=400)
    if note < 0 or note > 5:
        return JsonResponse({"ok": False, "error": "invalid"}, status=400)
    qs = _archives_queryset_for_etudiant(request)
    archive = get_object_or_404(qs, pk=pk)
    if note == 0:
        NoteArchive.objects.filter(user=request.user, archive=archive).delete()
    else:
        NoteArchive.objects.update_or_create(
            user=request.user,
            archive=archive,
            defaults={"note": note},
        )
    agg = NoteArchive.objects.filter(archive=archive).aggregate(avg=Avg("note"), n=Count("id"))
    avg = agg["avg"]
    return JsonResponse(
        {
            "ok": True,
            "moyenne": round(float(avg), 1) if avg is not None else None,
            "nb_votes": agg["n"] or 0,
            "user_note": note or None,
        }
    )


@login_required
def etudiant_commenter_archive(request, pk: int):
    """Page commentaire pour un sujet (archive) côté étudiant."""
    if not user_est_etudiant(request.user):
        raise Http404()
    qs = _archives_queryset_for_etudiant(request)
    archive = get_object_or_404(qs, pk=pk)
    if request.method == "POST":
        texte = (request.POST.get("commentaire") or "").strip()
        if texte:
            if archive.examen_id:
                Commentaire.objects.create(
                    user=request.user,
                    examen_id=archive.examen_id,
                    contenu=texte,
                )
            else:
                CommentaireArchive.objects.create(
                    user=request.user,
                    archive=archive,
                    contenu=texte,
                )
            messages.success(request, "Votre commentaire a été enregistré.")
            return redirect("etudiant_commenter_archive", pk=archive.pk)
        messages.error(request, "Merci de saisir un commentaire avant d'envoyer.")
    if archive.examen_id:
        commentaires_exam = Commentaire.objects.filter(examen_id=archive.examen_id)
    else:
        commentaires_exam = CommentaireArchive.objects.filter(archive=archive)
    commentaires = commentaires_exam.select_related("user").order_by("-date_creation")
    return render(
        request,
        "etudiant_commentaires.html",
        {"archive": archive, "commentaires": commentaires},
    )


@login_required
def telecharger_archive_etudiant(request, pk: int):
    """Permet à un étudiant de télécharger le PDF (incrémente nb_telechargements uniquement)."""
    if not user_est_etudiant(request.user):
        raise Http404()
    qs = _archives_queryset_for_etudiant(request)
    archive = get_object_or_404(qs, pk=pk)
    if not archive.fichier:
        raise Http404("Aucun fichier associé.")
    if not archive.fichier.storage.exists(archive.fichier.name):
        messages.error(request, "Le fichier PDF demandé est introuvable.")
        return redirect("espace_etudiant")
    archive.nb_telechargements += 1
    archive.save(update_fields=["nb_telechargements"])
    TelechargementEtudiant.objects.create(user=request.user, archive=archive)
    if archive.examen_id:
        obj, _ = Historique.objects.get_or_create(
            user=request.user,
            examen_id=archive.examen_id,
            defaults={},
        )
        obj.date_vue = timezone.now()
        obj.save(update_fields=["date_vue"])
    else:
        try:
            obj, _ = HistoriqueArchive.objects.get_or_create(
                user=request.user,
                archive=archive,
                defaults={},
            )
            obj.date_vue = timezone.now()
            obj.save(update_fields=["date_vue"])
        except ProgrammingError:
            pass
    response = FileResponse(archive.fichier.open("rb"), content_type="application/pdf")
    response["Content-Disposition"] = "attachment; filename*=UTF-8''" + _safe_filename(archive)
    return response


def _safe_filename(archive) -> str:
    """Nom de fichier sûr pour Content-Disposition (percent-encoded pour RFC 5987)."""
    from urllib.parse import quote
    base = (archive.title or "document").strip()
    base = "".join(c if c.isalnum() or c in ".-_ " else "_" for c in base)[:80].strip() or "document"
    return quote(base + ".pdf", safe="")


def _safe_filename_corrige(archive) -> str:
    from urllib.parse import quote
    base = (archive.title or "document").strip()
    base = "".join(c if c.isalnum() or c in ".-_ " else "_" for c in base)[:80].strip() or "document"
    return quote(base + "_corrige.pdf", safe="")


def _abonnement_etudiant_actif_pour_niveau(user):
    """
    Abonnement valide uniquement pour le niveau actuel de l'étudiant.
    Si le niveau a changé, l'abonnement actif est automatiquement désactivé.
    """
    abonnement = AbonnementEtudiant.objects.filter(user=user).first()
    etudiant = getattr(user, "etudiant", None)
    if (
        not abonnement
        or not abonnement.actif
        or abonnement.statut_demande != "approuvee"
        or not etudiant
    ):
        return False
    if abonnement.niveau_activation_id != etudiant.niveau_id:
        abonnement.actif = False
        abonnement.statut_demande = "aucune"
        abonnement.save(update_fields=["actif", "statut_demande", "date_mise_a_jour"])
        return False
    return True


def _context_quota_corrige(user, archives_qs=None):
    """
    Contexte d'accès corrigés :
    - 5 corrigés gratuits sur 5 matières différentes
    - ou abonnement actif (accès illimité au niveau de l'étudiant)
    """
    ids = list(
        ConsultationCorrigeGratuite.objects.filter(user=user).values_list("archive_id", flat=True)
    )
    modules_utilises = list(
        ConsultationCorrigeGratuite.objects.filter(user=user)
        .values_list("archive__module", flat=True)
        .distinct()
    )
    n = len(ids)
    abonnement_actif = _abonnement_etudiant_actif_pour_niveau(user)
    archives_accessibles = set(ids)
    if archives_qs is not None:
        for a in archives_qs:
            if not getattr(a, "fichier_corrige", None):
                continue
            if abonnement_actif:
                archives_accessibles.add(a.pk)
                continue
            if a.pk in archives_accessibles:
                continue
            if len(archives_accessibles) >= CORRIGE_GRATUITS_MAX:
                continue
            if a.module in modules_utilises:
                continue
            archives_accessibles.add(a.pk)

    return {
        "corrige_archives_debloques": ids,
        "corrige_archives_accessibles": list(archives_accessibles),
        "corrige_modules_utilises": modules_utilises,
        "corrige_gratuits_restants": max(0, CORRIGE_GRATUITS_MAX - n),
        "corrige_gratuits_max": CORRIGE_GRATUITS_MAX,
        "abonnement_etudiant_actif": abonnement_actif,
        "abonnement_etudiant_prix_usd": ABONNEMENT_ETUDIANT_PRIX_USD,
    }


def _reserver_accès_corrige_gratuit(request, archive):
    """
    Autorise l'accès au corrigé : au plus CORRIGE_GRATUITS_MAX archives distinctes
    par utilisateur ; les réouvertures du même corrigé restent gratuites.
    Retourne une HttpResponse 403 si quota dépassé, sinon None.
    """
    user = request.user
    if _abonnement_etudiant_actif_pour_niveau(user):
        return None
    if ConsultationCorrigeGratuite.objects.filter(user=user, archive=archive).exists():
        return None
    consultations = ConsultationCorrigeGratuite.objects.filter(user=user).select_related("archive")
    if consultations.count() >= CORRIGE_GRATUITS_MAX:
        messages.warning(
            request,
            "Vos 5 corrigés gratuits sont épuisés. Abonnez-vous pour continuer.",
        )
        return redirect("etudiant_abonnement")
    modules_deja_utilises = set(
        consultations.values_list("archive__module", flat=True)
    )
    if archive.module in modules_deja_utilises:
        messages.info(
            request,
            "Les 5 corrigés gratuits doivent provenir de 5 matières différentes. "
            "Abonnez-vous pour débloquer ce corrigé.",
        )
        return redirect("etudiant_abonnement")
    ConsultationCorrigeGratuite.objects.create(user=user, archive=archive)
    return None


def _normalize_card_number(raw: str) -> str:
    return "".join(ch for ch in (raw or "") if ch.isdigit())


def _is_demo_card_allowed(card_brand: str, card_number: str) -> bool:
    demo_cards = {
        "visa": {
            "4242424242424242",
            "4111111111111111",
        },
        "mastercard": {
            "5555555555554444",
            "2223003122003222",
        },
    }
    return card_number in demo_cards.get(card_brand, set())


@login_required
def etudiant_abonnement(request):
    """Page abonnement étudiant."""
    if not user_est_etudiant(request.user):
        raise Http404()
    abonnement, _ = AbonnementEtudiant.objects.get_or_create(
        user=request.user,
        defaults={"montant_usd": ABONNEMENT_ETUDIANT_PRIX_USD},
    )
    payment_provider = (getattr(settings, "PAYMENT_PROVIDER", "mastercard_demo") or "mastercard_demo").strip().lower()

    abonnement_actif_niveau = _abonnement_etudiant_actif_pour_niveau(request.user)
    if abonnement.actif and not abonnement_actif_niveau:
        messages.info(
            request,
            "Votre niveau a changé : l'abonnement précédent est clôturé. "
            "Vous disposez du quota gratuit puis vous pouvez reprendre l'abonnement pour ce nouveau niveau.",
        )
    quota_ctx = _context_quota_corrige(request.user)
    return render(
        request,
        "etudiant_abonnement.html",
        {
            "etudiant": request.user.etudiant,
            "abonnement": abonnement,
            "abonnement_prix_usd": ABONNEMENT_ETUDIANT_PRIX_USD,
            "payment_provider": payment_provider,
            "demande_abonnement_en_attente": abonnement.statut_demande == "en_attente",
            "demande_abonnement_rejetee": abonnement.statut_demande == "rejetee",
            **quota_ctx,
        },
    )


def _soumettre_demande_abonnement_apres_paiement(*, abonnement, etudiant):
    """Après paiement validé: la demande reste en attente de validation admin."""
    abonnement.actif = False
    abonnement.statut_demande = "en_attente"
    abonnement.montant_usd = ABONNEMENT_ETUDIANT_PRIX_USD
    abonnement.niveau_activation = etudiant.niveau
    abonnement.date_demande = abonnement.date_demande or timezone.now()
    abonnement.date_activation = None
    abonnement.date_traitement = None
    abonnement.save(
        update_fields=[
            "actif",
            "statut_demande",
            "montant_usd",
            "niveau_activation",
            "date_demande",
            "date_activation",
            "date_traitement",
            "date_mise_a_jour",
        ]
    )


@login_required
@require_POST
def etudiant_creer_session_paiement(request):
    if not user_est_etudiant(request.user):
        raise Http404()
    abonnement, _ = AbonnementEtudiant.objects.get_or_create(
        user=request.user,
        defaults={"montant_usd": ABONNEMENT_ETUDIANT_PRIX_USD},
    )
    if _abonnement_etudiant_actif_pour_niveau(request.user):
        messages.info(request, "Votre abonnement est déjà actif pour votre niveau actuel.")
        return redirect("etudiant_abonnement")

    card_brand = (request.POST.get("card_brand") or "").strip().lower()
    card_number = _normalize_card_number(request.POST.get("card_number") or "")
    card_expiry = (request.POST.get("card_expiry") or "").strip()
    card_cvv = _normalize_card_number(request.POST.get("card_cvv") or "")
    holder_name = (request.POST.get("holder_name") or "").strip()
    if card_brand not in {"visa", "mastercard"}:
        messages.error(request, "Choisissez Visa ou MasterCard.")
        return redirect("etudiant_abonnement")
    if len(card_number) < 13 or len(card_number) > 19:
        messages.error(request, "Le numero de carte doit contenir entre 13 et 19 chiffres.")
        return redirect("etudiant_abonnement")
    if len(card_cvv) not in {3, 4} or not card_expiry or not holder_name:
        messages.error(request, "Informations de paiement invalides. Verifiez le formulaire.")
        return redirect("etudiant_abonnement")

    payment_provider = (getattr(settings, "PAYMENT_PROVIDER", "mastercard_demo") or "mastercard_demo").strip().lower()
    paiement = PaiementAbonnement.objects.create(
        user=request.user,
        abonnement=abonnement,
        provider="mastercard",
        statut="initie",
        montant_usd=ABONNEMENT_ETUDIANT_PRIX_USD,
        devise=getattr(settings, "MASTERCARD_CURRENCY", "USD"),
    )
    paiement.gateway_order_id = f"SIGAEUD-{paiement.reference.hex[:20]}"
    paiement.save(update_fields=["gateway_order_id", "date_mise_a_jour"])

    service = MastercardCheckoutService(settings)
    local_mode = (payment_provider == "mastercard_demo") or (payment_provider == "mastercard_sandbox" and not service.is_configured())
    checkout_url = reverse_lazy("etudiant_paiement_checkout", kwargs={"tx_ref": paiement.reference})

    if local_mode:
        if not _is_demo_card_allowed(card_brand, card_number):
            paiement.statut = "echoue"
            paiement.message = "Carte de test non reconnue en mode local."
            paiement.save(update_fields=["statut", "message", "date_mise_a_jour"])
            messages.error(request, "Carte non reconnue. Utilisez une carte test fournie.")
            return redirect("etudiant_abonnement")
        _soumettre_demande_abonnement_apres_paiement(
            abonnement=abonnement,
            etudiant=request.user.etudiant,
        )
        paiement.statut = "reussi"
        paiement.date_validation = timezone.now()
        paiement.message = "Paiement local simulé validé. Demande envoyée à l'administrateur."
        paiement.payload_gateway = {"mode": "local_simulation"}
        paiement.save(
            update_fields=[
                "statut",
                "date_validation",
                "message",
                "payload_gateway",
                "date_mise_a_jour",
            ]
        )
        messages.success(
            request,
            "Paiement validé. Votre demande d'abonnement est en attente de validation par l'administrateur.",
        )
        return redirect("etudiant_abonnement")

    try:
        app_base = (getattr(settings, "APP_BASE_URL", "") or "").rstrip("/")
        return_url = f"{app_base}{reverse_lazy('etudiant_paiement_retour')}?tx={paiement.reference}"
        cancel_url = f"{app_base}{reverse_lazy('etudiant_paiement_retour')}?tx={paiement.reference}&status=cancelled"
        response = service.create_checkout_session(
            order_id=paiement.gateway_order_id,
            amount=ABONNEMENT_ETUDIANT_PRIX_USD,
            currency=getattr(settings, "MASTERCARD_CURRENCY", "USD"),
            return_url=return_url,
            cancel_url=cancel_url,
            customer_email=request.user.email,
            customer_name=request.user.get_full_name() or request.user.username,
        )
    except Exception as exc:
        logger.exception("Erreur creation session Mastercard: %s", exc)
        paiement.statut = "erreur"
        paiement.message = "Erreur reseau lors de la creation de session Mastercard."
        paiement.save(update_fields=["statut", "message", "date_mise_a_jour"])
        messages.error(request, "Impossible de contacter la passerelle de paiement. Réessayez.")
        return redirect("etudiant_abonnement")

    session_id = (response.get("session") or {}).get("id") if isinstance(response, dict) else None
    success_indicator = response.get("successIndicator", "") if isinstance(response, dict) else ""
    if not session_id:
        paiement.statut = "erreur"
        paiement.message = "Session Mastercard invalide."
        paiement.payload_gateway = response
        paiement.save(update_fields=["statut", "message", "payload_gateway", "date_mise_a_jour"])
        messages.error(request, "La session de paiement n'a pas pu être créée.")
        return redirect("etudiant_abonnement")

    paiement.statut = "en_attente"
    paiement.gateway_session_id = session_id
    paiement.gateway_success_indicator = success_indicator or ""
    paiement.payload_gateway = response
    paiement.save(
        update_fields=[
            "statut",
            "gateway_session_id",
            "gateway_success_indicator",
            "payload_gateway",
            "date_mise_a_jour",
        ]
    )
    return redirect(checkout_url)


@login_required
def etudiant_paiement_checkout(request, tx_ref):
    if not user_est_etudiant(request.user):
        raise Http404()
    paiement = get_object_or_404(PaiementAbonnement, reference=tx_ref, user=request.user)
    payload = paiement.payload_gateway or {}
    is_local_mode = ((payload.get("mode") == "local_simulation") if isinstance(payload, dict) else False) or not paiement.gateway_session_id
    return render(
        request,
        "etudiant_paiement_checkout.html",
        {
            "paiement": paiement,
            "is_local_mode": is_local_mode,
            "gateway_url": getattr(settings, "MASTERCARD_GATEWAY_URL", "").rstrip("/"),
            "gateway_api_version": getattr(settings, "MASTERCARD_API_VERSION", "100"),
            "merchant_id": getattr(settings, "MASTERCARD_MERCHANT_ID", ""),
            "return_url": f"{(getattr(settings, 'APP_BASE_URL', '') or '').rstrip('/')}{reverse_lazy('etudiant_paiement_retour')}?tx={paiement.reference}",
            "cancel_url": f"{(getattr(settings, 'APP_BASE_URL', '') or '').rstrip('/')}{reverse_lazy('etudiant_paiement_retour')}?tx={paiement.reference}&status=cancelled",
        },
    )


@login_required
def etudiant_paiement_retour(request):
    if not user_est_etudiant(request.user):
        raise Http404()
    tx = (request.GET.get("tx") or "").strip()
    if not tx:
        messages.error(request, "Retour de paiement invalide.")
        return redirect("etudiant_abonnement")
    paiement = get_object_or_404(PaiementAbonnement, reference=tx, user=request.user)

    status_hint = (request.GET.get("status") or "").strip().lower()
    if status_hint == "cancelled":
        paiement.statut = "annule"
        paiement.message = "Paiement annulé par l'utilisateur."
        paiement.save(update_fields=["statut", "message", "date_mise_a_jour"])
        messages.warning(request, "Paiement annulé. Aucun accès supplémentaire n'a été débloqué.")
        return redirect("etudiant_abonnement")

    payload = paiement.payload_gateway or {}
    local_mode = (payload.get("mode") == "local_simulation") if isinstance(payload, dict) else False
    if local_mode:
        messages.info(
            request,
            "Votre paiement local est déjà pris en compte et envoyé en attente de validation administrateur.",
        )
        return redirect("etudiant_abonnement")

    service = MastercardCheckoutService(settings)
    if not service.is_configured():
        paiement.statut = "erreur"
        paiement.message = "Configuration sandbox Mastercard incomplète."
        paiement.save(update_fields=["statut", "message", "date_mise_a_jour"])
        messages.error(request, "Configuration paiement incomplète côté serveur.")
        return redirect("etudiant_abonnement")
    try:
        order_data = service.retrieve_order(paiement.gateway_order_id)
    except Exception as exc:
        logger.exception("Erreur verification paiement Mastercard: %s", exc)
        paiement.statut = "erreur"
        paiement.message = "Erreur reseau lors de la verification du paiement."
        paiement.save(update_fields=["statut", "message", "date_mise_a_jour"])
        messages.error(request, "Vérification impossible pour le moment. Réessayez dans quelques instants.")
        return redirect("etudiant_abonnement")

    result = (order_data.get("result") or "").upper() if isinstance(order_data, dict) else ""
    order_status = ((order_data.get("order") or {}).get("status") or "").upper() if isinstance(order_data, dict) else ""
    if result == "SUCCESS" or order_status in {"CAPTURED", "PAID"}:
        abonnement = paiement.abonnement or AbonnementEtudiant.objects.get(user=request.user)
        _soumettre_demande_abonnement_apres_paiement(
            abonnement=abonnement,
            etudiant=request.user.etudiant,
        )
        paiement.statut = "reussi"
        paiement.message = "Paiement Mastercard validé."
        paiement.date_validation = timezone.now()
        paiement.payload_gateway = order_data
        paiement.save(
            update_fields=["statut", "message", "date_validation", "payload_gateway", "date_mise_a_jour"]
        )
        messages.success(
            request,
            "Paiement réussi. Votre demande d'abonnement est maintenant en attente de validation par l'administrateur.",
        )
    else:
        paiement.statut = "echoue"
        paiement.message = f"Paiement non validé (result={result}, order_status={order_status})."
        paiement.payload_gateway = order_data
        paiement.save(update_fields=["statut", "message", "payload_gateway", "date_mise_a_jour"])
        messages.error(request, "Paiement échoué ou non confirmé. Aucun accès n'a été débloqué.")
    return redirect("etudiant_abonnement")


@login_required
def toggle_favori_etudiant(request, pk: int):
    """Ajoute ou retire une archive des favoris (par examen si lié, sinon par archive directe)."""
    if not user_est_etudiant(request.user):
        raise Http404()
    qs = _archives_queryset_for_etudiant(request)
    archive = get_object_or_404(qs, pk=pk)
    next_url = request.GET.get("next") or request.POST.get("next") or request.META.get("HTTP_REFERER") or "espace_etudiant"
    if archive.examen_id:
        favori, created = Favori.objects.get_or_create(
            user=request.user,
            examen_id=archive.examen_id,
        )
        if created:
            messages.success(request, "Ajouté aux favoris.")
        else:
            favori.delete()
            messages.success(request, "Retiré des favoris.")
    else:
        try:
            favori_arch, created = FavoriArchive.objects.get_or_create(
                user=request.user,
                archive=archive,
            )
            if created:
                messages.success(request, "Ajouté aux favoris.")
            else:
                favori_arch.delete()
                messages.success(request, "Retiré des favoris.")
        except ProgrammingError:
            messages.info(request, "Fonctionnalité favoris (archives) en cours de déploiement. Exécutez: python manage.py migrate")
    return redirect(next_url)


@login_required
def retirer_favori_etudiant(request, examen_id: int):
    """Retire un examen des favoris (sans avoir besoin d'une archive)."""
    if not user_est_etudiant(request.user):
        raise Http404()
    deleted, _ = Favori.objects.filter(user=request.user, examen_id=examen_id).delete()
    if deleted:
        messages.success(request, "Retiré des favoris.")
    next_url = request.GET.get("next") or request.META.get("HTTP_REFERER") or "etudiant_favoris"
    return redirect(next_url)


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
@require_POST
def supprimer_archive(request, pk: int):
    qs = _archives_queryset_for_user(request)
    archive = get_object_or_404(qs, pk=pk)
    archive.delete()
    messages.success(request, "L'archive a été supprimée.")
    return redirect("personnel")


# --- Tableau de bord admin (mêmes données que admin.py) ---

def _format_activity_ago(dt):
    """Retourne « il y a X min », « il y a X h », « il y a X j »."""
    if not dt:
        return ""
    from django.utils import timezone
    now = timezone.now()
    if timezone.is_naive(dt):
        from django.utils.timezone import make_aware
        dt = make_aware(dt) if timezone.get_current_timezone() else dt
    delta = now - dt
    total_seconds = int(delta.total_seconds())
    if total_seconds < 60:
        return "à l'instant"
    if total_seconds < 3600:
        m = total_seconds // 60
        return f"il y a {m} min"
    if total_seconds < 86400:
        h = total_seconds // 3600
        return f"il y a {h} h"
    d = total_seconds // 86400
    return f"il y a {d} j"


def _dashboard_user_role(user):
    """Badge rôle pour le tableau de bord (étudiant, enseignant, etc.)."""
    from django.core.exceptions import ObjectDoesNotExist

    if user.is_superuser:
        return "admin", "Admin"
    try:
        user.etudiant
        return "student", "Étudiant"
    except ObjectDoesNotExist:
        pass
    try:
        user.assistant_pedagogique
        return "assistant", "Assistant"
    except ObjectDoesNotExist:
        pass
    if user.is_staff:
        return "teacher", "Enseignant"
    return "user", "Utilisateur"


def _growth_pct(recent_count, prev_count):
    """Pourcentage d’évolution entre deux périodes (30 j glissants)."""
    if prev_count == 0:
        return None if recent_count == 0 else 100
    return round((recent_count - prev_count) / prev_count * 100)


def _redirect_si_pas_admin_sigaud(request):
    """Redirige vers l'accueil avec message si l'utilisateur n'a pas accès admin Sigaeud."""
    if user_est_admin_sigaud(request.user):
        return None
    messages.warning(request, "Accès réservé aux administrateurs.")
    return redirect("accueil")


@login_required
def admin_dashboard(request):
    """Tableau de bord Sigaeud : staff, superuser ou groupe Administrateur système."""
    denied = _redirect_si_pas_admin_sigaud(request)
    if denied:
        return denied
    from datetime import date

    from django.contrib.auth import get_user_model
    from django.db.models import Count
    from django.db.models.functions import TruncMonth
    from django.contrib.admin.models import LogEntry

    User = get_user_model()
    total_users = User.objects.count()
    total_archives = Archive.objects.count()
    total_facultes = Faculte.objects.count()
    total_filieres = Filiere.objects.count()

    today = timezone.now().date()
    d30 = today - timedelta(days=30)
    d60 = today - timedelta(days=60)

    users_recent = User.objects.filter(date_joined__date__gte=d30).count()
    users_prev = User.objects.filter(date_joined__date__gte=d60, date_joined__date__lt=d30).count()
    growth_users_pct = _growth_pct(users_recent, users_prev)

    archives_recent = Archive.objects.filter(date_archive__gte=d30).count()
    archives_prev = Archive.objects.filter(date_archive__gte=d60, date_archive__lt=d30).count()
    growth_archives_pct = _growth_pct(archives_recent, archives_prev)

    recent_users = (
        User.objects.select_related("etudiant", "assistant_pedagogique")
        .order_by("-date_joined")[:8]
    )
    dashboard_user_rows = []
    for u in recent_users:
        kind, label = _dashboard_user_role(u)
        dashboard_user_rows.append(
            {
                "user": u,
                "role_kind": kind,
                "role_label": label,
            }
        )

    facultes_avec_filieres = (
        Faculte.objects.annotate(nb_filieres=Count("filieres"))
        .order_by("libelle")[:12]
    )

    log_notifications_count = LogEntry.objects.filter(
        action_time__gte=timezone.now() - timedelta(days=7)
    ).count()
    demandes_abonnement_en_attente = AbonnementEtudiant.objects.filter(
        statut_demande="en_attente"
    ).count()
    notification_count = log_notifications_count + demandes_abonnement_en_attente

    # Donnees graphiques dynamiques (un graphe a la fois dans le dashboard)
    user_monthly = {}
    for row in (
        User.objects.annotate(m=TruncMonth("date_joined"))
        .values("m")
        .annotate(c=Count("id"))
        .order_by("m")
    ):
        if row["m"]:
            key = (row["m"].year, row["m"].month)
            user_monthly[key] = user_monthly.get(key, 0) + row["c"]

    archive_monthly = {}
    for row in (
        Archive.objects.annotate(m=TruncMonth("date_archive"))
        .values("m")
        .annotate(c=Count("id"))
        .order_by("m")
    ):
        if row["m"]:
            key = (row["m"].year, row["m"].month)
            archive_monthly[key] = archive_monthly.get(key, 0) + row["c"]

    today_local = timezone.localdate()
    end_ym = (today_local.year, today_local.month)
    all_keys = list(user_monthly.keys()) + list(archive_monthly.keys())
    start_ym = min(all_keys) if all_keys else end_ym
    months = _sigaud_months_range(start_ym, end_ym)
    if len(months) > 48:
        months = months[-48:]
        start_ym = months[0]

    def first_day(ym):
        return date(ym[0], ym[1], 1)

    base_users = User.objects.filter(date_joined__lt=first_day(start_ym)).count()
    base_archives = Archive.objects.filter(date_archive__lt=first_day(start_ym)).count()

    labels_time = []
    users_cumul = []
    archives_cumul = []
    cu, ca = base_users, base_archives
    for ym in months:
        cu += user_monthly.get(ym, 0)
        ca += archive_monthly.get(ym, 0)
        labels_time.append(_sigaud_label_mois_fr(*ym))
        users_cumul.append(cu)
        archives_cumul.append(ca)

    fil_rows = list(
        Archive.objects.values("filiere").annotate(nb=Count("id")).order_by("-nb")
    )
    top_fil = 8
    fil_labels = [
        (r["filiere"] or "(Non renseigne)").strip() or "(Non renseigne)"
        for r in fil_rows[:top_fil]
    ]
    fil_values = [r["nb"] for r in fil_rows[:top_fil]]
    if len(fil_rows) > top_fil:
        autres = sum(r["nb"] for r in fil_rows[top_fil:])
        if autres:
            fil_labels.append("Autres")
            fil_values.append(autres)

    type_rows = list(
        Archive.objects.values("type").annotate(nb=Count("id")).order_by("-nb")
    )
    type_labels = [
        (r["type"] or "(Non renseigne)").strip() or "(Non renseigne)" for r in type_rows
    ]
    type_values = [r["nb"] for r in type_rows]

    dashboard_charts = [
        {
            "key": "users_growth",
            "title": "Evolution des utilisateurs",
            "subtitle": "Nombre cumule de comptes par mois",
            "type": "line",
            "labels": labels_time,
            "values": users_cumul,
            "color": "#5b21b6",
        },
        {
            "key": "archives_growth",
            "title": "Evolution des sujets archives",
            "subtitle": "Nombre cumule d'archives par mois",
            "type": "line",
            "labels": labels_time,
            "values": archives_cumul,
            "color": "#0d9488",
        },
        {
            "key": "filiere_share",
            "title": "Repartition des sujets par filiere",
            "subtitle": "Top filieres + autres",
            "type": "doughnut",
            "labels": fil_labels,
            "values": fil_values,
        },
        {
            "key": "type_share",
            "title": "Repartition par type d'epreuve",
            "subtitle": "CC versus Examen final",
            "type": "doughnut",
            "labels": type_labels,
            "values": type_values,
        },
    ]

    return render(
        request,
        "admin.html",
        {
            "total_users": total_users,
            "total_archives": total_archives,
            "total_facultes": total_facultes,
            "total_filieres": total_filieres,
            "growth_users_pct": growth_users_pct,
            "growth_archives_pct": growth_archives_pct,
            "recent_users": recent_users,
            "dashboard_user_rows": dashboard_user_rows,
            "facultes_avec_filieres": facultes_avec_filieres,
            "notification_count": notification_count,
            "demandes_abonnement_en_attente": demandes_abonnement_en_attente,
            "dashboard_charts": dashboard_charts,
        },
    )


@login_required
def admin_utilisateurs(request):
    """Liste des utilisateurs avec recherche et filtres (style Django admin)."""
    denied = _redirect_si_pas_admin_sigaud(request)
    if denied:
        return denied
    from django.contrib.auth import get_user_model
    from django.contrib.auth.models import Group

    User = get_user_model()
    qs = User.objects.all().order_by("username")

    # Recherche (username, email, first_name, last_name)
    q = (request.GET.get("q") or "").strip()
    if q:
        from django.db.models import Q
        qs = qs.filter(
            Q(username__icontains=q)
            | Q(email__icontains=q)
            | Q(first_name__icontains=q)
            | Q(last_name__icontains=q)
        )

    # Filtre par statut staff
    staff_status = request.GET.get("staff_status", "all")
    if staff_status == "yes":
        qs = qs.filter(is_staff=True)
    elif staff_status == "no":
        qs = qs.filter(is_staff=False)

    # Filtre par statut superuser
    superuser_status = request.GET.get("superuser_status", "all")
    if superuser_status == "yes":
        qs = qs.filter(is_superuser=True)
    elif superuser_status == "no":
        qs = qs.filter(is_superuser=False)

    # Filtre par actif
    is_active_filter = request.GET.get("is_active", "all")
    if is_active_filter == "yes":
        qs = qs.filter(is_active=True)
    elif is_active_filter == "no":
        qs = qs.filter(is_active=False)

    # Filtre par groupe
    group_name = request.GET.get("group", "")
    if group_name:
        qs = qs.filter(groups__name=group_name).distinct()

    users = qs
    user_rows = []
    for u in users:
        role_kind, role_label = _dashboard_user_role(u)
        user_rows.append(
            {
                "user": u,
                "role_kind": role_kind,
                "role_label": role_label,
            }
        )
    groups = Group.objects.all().order_by("name")

    return render(
        request,
        "admin_utilisateurs.html",
        {
            "users": users,
            "user_rows": user_rows,
            "groups": groups,
            "total_count": users.count(),
            "query": q,
            "staff_status": staff_status,
            "superuser_status": superuser_status,
            "is_active_filter": is_active_filter,
            "selected_group": group_name,
        },
    )


@login_required
def admin_add_user(request):
    """Page « Add user » style Django admin (en-tête bleu-vert, sidebar, formulaire + profil assistant)."""
    denied = _redirect_si_pas_admin_sigaud(request)
    if denied:
        return denied
    from .forms import AdminAddUserForm

    form = AdminAddUserForm()
    if request.method == "POST":
        form = AdminAddUserForm(request.POST)
        if form.is_valid():
            try:
                new_user = form.save()
            except IntegrityError:
                # Sécurité anti-race condition :
                # si un username/email est créé juste avant l'enregistrement,
                # on affiche l'erreur dans le formulaire au lieu d'une page 500.
                username = (form.cleaned_data.get("username") or "").strip()
                email = (form.cleaned_data.get("email") or "").strip().lower()
                UserModel = get_user_model()
                if username and UserModel.objects.filter(username__iexact=username).exists():
                    form.add_error("username", "Un utilisateur avec ce nom d'utilisateur existe déjà.")
                if email and UserModel.objects.filter(email__iexact=email).exists():
                    form.add_error("email", "Cette adresse email est déjà utilisée.")
                if not form.errors:
                    form.add_error(None, "Impossible d'enregistrer ce compte. Veuillez vérifier les informations saisies.")
            else:
                messages.success(request, f"L'utilisateur « {new_user.username } » a été créé.")
                action = request.POST.get("_action", "save")
                if action == "add_another":
                    return redirect("admin_add_user")
                if action == "continue":
                    return redirect("admin_modifier_utilisateur", pk=new_user.pk)
                return redirect("admin_utilisateurs")
    return render(request, "admin_add_user.html", {"form": form})


@login_required
def admin_modifier_utilisateur(request, pk: int):
    """Edition d'un utilisateur dans l'UI admin SIGAEUD (sans admin Django)."""
    denied = _redirect_si_pas_admin_sigaud(request)
    if denied:
        return denied
    User = get_user_model()
    target_user = get_object_or_404(User, pk=pk)

    form = AdminEditUserForm(target_user)
    if request.method == "POST":
        form = AdminEditUserForm(target_user, request.POST)
        if request.POST.get("_reload_form") == "1":
            pass
        elif form.is_valid():
            updated_user = form.save()
            messages.success(
                request,
                f"L'utilisateur « {updated_user.username} » a été mis à jour.",
            )
            action = request.POST.get("_action", "save")
            if action == "continue":
                return redirect("admin_modifier_utilisateur", pk=updated_user.pk)
            return redirect("admin_utilisateurs")

    return render(
        request,
        "admin_modifier_utilisateur.html",
        {
            "form": form,
            "target_user": target_user,
            "role_utilisateur": form.user_role,
        },
    )


@login_required
@require_POST
def admin_supprimer_utilisateur(request, pk: int):
    """Suppression d'un utilisateur depuis l'interface admin SIGAEUD."""
    denied = _redirect_si_pas_admin_sigaud(request)
    if denied:
        return denied
    User = get_user_model()
    target_user = get_object_or_404(User, pk=pk)

    if target_user.pk == request.user.pk:
        messages.error(request, "Vous ne pouvez pas supprimer votre propre compte connecté.")
        return redirect("admin_modifier_utilisateur", pk=target_user.pk)

    username = target_user.username
    try:
        target_user.delete()
    except (ProtectedError, RestrictedError, IntegrityError, DatabaseError):
        # Fallback robuste si la suppression physique echoue
        # (contraintes FK, table legacy manquante, schema incomplet, etc.).
        target_user.is_active = False
        target_user.save(update_fields=["is_active"])
        messages.warning(
            request,
            "Suppression technique impossible (references en base). "
            "Le compte a ete desactive a la place.",
        )
        return redirect("admin_modifier_utilisateur", pk=target_user.pk)
    messages.success(request, f"L'utilisateur « {username} » a été supprimé.")
    return redirect("admin_utilisateurs")


@login_required
def admin_documents(request):
    """Liste des archives/documents (données comme admin)."""
    denied = _redirect_si_pas_admin_sigaud(request)
    if denied:
        return denied
    documents = Archive.objects.all().order_by("-date_archive")
    return render(request, "admin_documents.html", {"documents": documents})


@login_required
def admin_ajouter_archive(request):
    """Ajout d'une archive depuis l'espace admin SIGAEUD."""
    denied = _redirect_si_pas_admin_sigaud(request)
    if denied:
        return denied
    if request.method == "POST":
        form = ArchiveForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "L'archive a ete ajoutee.")
            return redirect("admin_documents")
    else:
        form = ArchiveForm()
    return render(
        request,
        "archive_form.html",
        {
            "form": form,
            "archive": None,
            "page_title": "Ajouter une archive",
            "page_help": "Renseignez les informations du sujet puis validez l'ajout.",
            "cancel_url_name": "admin_documents",
            "submit_label": "Ajouter l'archive",
        },
    )


@login_required
def admin_modifier_archive(request, pk: int):
    """Modification d'une archive depuis l'espace admin SIGAEUD."""
    denied = _redirect_si_pas_admin_sigaud(request)
    if denied:
        return denied
    archive = get_object_or_404(Archive, pk=pk)
    if request.method == "POST":
        form = ArchiveForm(request.POST, request.FILES, instance=archive)
        if form.is_valid():
            form.save()
            messages.success(request, "L'archive a ete mise a jour.")
            return redirect("admin_documents")
    else:
        form = ArchiveForm(instance=archive)
    return render(
        request,
        "archive_form.html",
        {
            "form": form,
            "archive": archive,
            "page_title": "Modifier l'archive",
            "page_help": "Mettez a jour les informations du sujet puis enregistrez.",
            "cancel_url_name": "admin_documents",
            "submit_label": "Enregistrer les modifications",
        },
    )


@login_required
@require_POST
def admin_supprimer_archive(request, pk: int):
    """Suppression d'une archive depuis l'espace admin SIGAEUD."""
    denied = _redirect_si_pas_admin_sigaud(request)
    if denied:
        return denied
    archive = get_object_or_404(Archive, pk=pk)
    titre = archive.title
    archive.delete()
    messages.success(request, f"Archive supprimee : {titre}.")
    return redirect("admin_documents")


def _sigaud_months_range(start_ym, end_ym):
    """start_ym / end_ym: (year, month) avec start <= end."""
    y, m = start_ym
    ye, me = end_ym
    out = []
    while (y, m) <= (ye, me):
        out.append((y, m))
        m += 1
        if m > 12:
            m = 1
            y += 1
    return out


def _sigaud_label_mois_fr(y, m):
    mois = (
        "janv.",
        "févr.",
        "mars",
        "avr.",
        "mai",
        "juin",
        "juil.",
        "août",
        "sept.",
        "oct.",
        "nov.",
        "déc.",
    )
    return f"{mois[m - 1]} {y}"


@login_required
def admin_statistiques(request):
    """Statistiques : graphiques (évolution, répartitions)."""
    denied = _redirect_si_pas_admin_sigaud(request)
    if denied:
        return denied
    from datetime import date

    from django.db.models import Count
    from django.db.models.functions import TruncMonth

    User = get_user_model()
    total_archives = Archive.objects.count()
    total_utilisateurs = User.objects.count()

    user_monthly = {}
    for row in (
        User.objects.annotate(m=TruncMonth("date_joined"))
        .values("m")
        .annotate(c=Count("id"))
        .order_by("m")
    ):
        if row["m"]:
            dk = (row["m"].year, row["m"].month)
            user_monthly[dk] = user_monthly.get(dk, 0) + row["c"]

    archive_monthly = {}
    for row in (
        Archive.objects.annotate(m=TruncMonth("date_archive"))
        .values("m")
        .annotate(c=Count("id"))
        .order_by("m")
    ):
        if row["m"]:
            dk = (row["m"].year, row["m"].month)
            archive_monthly[dk] = archive_monthly.get(dk, 0) + row["c"]

    today = timezone.localdate()
    end_ym = (today.year, today.month)
    all_keys = list(user_monthly.keys()) + list(archive_monthly.keys())
    if all_keys:
        start_ym = min(all_keys)
    else:
        start_ym = end_ym

    months = _sigaud_months_range(start_ym, end_ym)
    max_span = 72
    if len(months) > max_span:
        months = months[-max_span:]
        start_ym = months[0]

    def first_day(ym):
        return date(ym[0], ym[1], 1)

    base_users = User.objects.filter(date_joined__lt=first_day(start_ym)).count()
    base_archives = Archive.objects.filter(date_archive__lt=first_day(start_ym)).count()

    labels_temps = []
    serie_utilisateurs_cumul = []
    serie_archives_cumul = []
    cu, ca = base_users, base_archives
    for ym in months:
        cu += user_monthly.get(ym, 0)
        ca += archive_monthly.get(ym, 0)
        labels_temps.append(_sigaud_label_mois_fr(*ym))
        serie_utilisateurs_cumul.append(cu)
        serie_archives_cumul.append(ca)

    chart_evolution_utilisateurs = {
        "labels": labels_temps,
        "values": serie_utilisateurs_cumul,
    }
    chart_evolution_archives = {
        "labels": labels_temps,
        "values": serie_archives_cumul,
    }

    fil_rows = list(
        Archive.objects.values("filiere")
        .annotate(nb=Count("id"))
        .order_by("-nb")
    )
    top_fil = 12
    if len(fil_rows) > top_fil:
        head = fil_rows[:top_fil]
        autres = sum(r["nb"] for r in fil_rows[top_fil:])
        labels_fil = [(r["filiere"] or "(Non renseigné)").strip() or "(Non renseigné)" for r in head]
        data_fil = [r["nb"] for r in head]
        if autres > 0:
            labels_fil.append("Autres")
            data_fil.append(autres)
    else:
        labels_fil = [
            (r["filiere"] or "(Non renseigné)").strip() or "(Non renseigné)" for r in fil_rows
        ]
        data_fil = [r["nb"] for r in fil_rows]

    chart_filiere = {"labels": labels_fil, "values": data_fil}

    type_rows = list(
        Archive.objects.values("type").annotate(nb=Count("id")).order_by("-nb")
    )
    chart_type = {
        "labels": [
            (r["type"] or "(Non renseigné)").strip() or "(Non renseigné)" for r in type_rows
        ],
        "values": [r["nb"] for r in type_rows],
    }

    mod_rows = list(
        Archive.objects.values("module")
        .annotate(nb=Count("id"))
        .order_by("-nb")[:10]
    )
    mod_labels = []
    for r in mod_rows:
        lab = (r["module"] or "(Non renseigné)").strip() or "(Non renseigné)"
        if len(lab) > 42:
            lab = lab[:39] + "…"
        mod_labels.append(lab)
    chart_modules = {"labels": mod_labels, "values": [r["nb"] for r in mod_rows]}

    return render(
        request,
        "admin_statistiques.html",
        {
            "total_archives": total_archives,
            "total_utilisateurs": total_utilisateurs,
            "chart_evolution_utilisateurs": chart_evolution_utilisateurs,
            "chart_evolution_archives": chart_evolution_archives,
            "chart_filiere": chart_filiere,
            "chart_type": chart_type,
            "chart_modules": chart_modules,
        },
    )


@login_required
def admin_facultes(request):
    """Liste des facultés (comme admin.py Facultés)."""
    denied = _redirect_si_pas_admin_sigaud(request)
    if denied:
        return denied
    from django.db.models import Count

    facultes = Faculte.objects.annotate(nb_filieres=Count("filieres")).order_by("code")
    filieres = Filiere.objects.select_related("faculte").order_by("faculte__code", "code")
    return render(
        request,
        "admin_facultes.html",
        {"facultes": facultes, "filieres": filieres},
    )


@login_required
def admin_ajouter_faculte(request):
    denied = _redirect_si_pas_admin_sigaud(request)
    if denied:
        return denied
    if request.method == "POST":
        form = FaculteForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Faculte ajoutee avec succes.")
            return redirect("admin_facultes")
    else:
        form = FaculteForm()
    return render(
        request,
        "admin_structure_form.html",
        {
            "form": form,
            "page_title": "Ajouter une faculte",
            "page_help": "Creer une nouvelle faculte academique.",
            "submit_label": "Ajouter",
            "cancel_url_name": "admin_facultes",
        },
    )


@login_required
def admin_modifier_faculte(request, pk: int):
    denied = _redirect_si_pas_admin_sigaud(request)
    if denied:
        return denied
    faculte = get_object_or_404(Faculte, pk=pk)
    if request.method == "POST":
        form = FaculteForm(request.POST, instance=faculte)
        if form.is_valid():
            form.save()
            messages.success(request, "Faculte modifiee avec succes.")
            return redirect("admin_facultes")
    else:
        form = FaculteForm(instance=faculte)
    return render(
        request,
        "admin_structure_form.html",
        {
            "form": form,
            "page_title": "Modifier la faculte",
            "page_help": "Mettez a jour les informations de la faculte.",
            "submit_label": "Enregistrer",
            "cancel_url_name": "admin_facultes",
        },
    )


@login_required
@require_POST
def admin_supprimer_faculte(request, pk: int):
    denied = _redirect_si_pas_admin_sigaud(request)
    if denied:
        return denied
    faculte = get_object_or_404(Faculte, pk=pk)
    try:
        faculte.delete()
        messages.success(request, "Faculte supprimee avec succes.")
    except (ProtectedError, RestrictedError, IntegrityError, DatabaseError):
        messages.error(
            request,
            "Suppression impossible: des filieres ou niveaux sont lies a cette faculte.",
        )
    return redirect("admin_facultes")


@login_required
def admin_ajouter_filiere(request):
    denied = _redirect_si_pas_admin_sigaud(request)
    if denied:
        return denied
    if request.method == "POST":
        form = FiliereForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Filiere ajoutee avec succes.")
            return redirect("admin_facultes")
    else:
        form = FiliereForm()
    return render(
        request,
        "admin_structure_form.html",
        {
            "form": form,
            "page_title": "Ajouter une filiere",
            "page_help": "Creer une nouvelle filiere/departement.",
            "submit_label": "Ajouter",
            "cancel_url_name": "admin_facultes",
        },
    )


@login_required
def admin_modifier_filiere(request, pk: int):
    denied = _redirect_si_pas_admin_sigaud(request)
    if denied:
        return denied
    filiere = get_object_or_404(Filiere, pk=pk)
    if request.method == "POST":
        form = FiliereForm(request.POST, instance=filiere)
        if form.is_valid():
            form.save()
            messages.success(request, "Filiere modifiee avec succes.")
            return redirect("admin_facultes")
    else:
        form = FiliereForm(instance=filiere)
    return render(
        request,
        "admin_structure_form.html",
        {
            "form": form,
            "page_title": "Modifier la filiere",
            "page_help": "Mettez a jour les informations de la filiere.",
            "submit_label": "Enregistrer",
            "cancel_url_name": "admin_facultes",
        },
    )


@login_required
@require_POST
def admin_supprimer_filiere(request, pk: int):
    denied = _redirect_si_pas_admin_sigaud(request)
    if denied:
        return denied
    filiere = get_object_or_404(Filiere, pk=pk)
    try:
        filiere.delete()
        messages.success(request, "Filiere supprimee avec succes.")
    except (ProtectedError, RestrictedError, IntegrityError, DatabaseError):
        messages.error(
            request,
            "Suppression impossible: des elements sont lies a cette filiere.",
        )
    return redirect("admin_facultes")


@login_required
def admin_parametres(request):
    """Page paramètres : lien vers l'admin Django."""
    denied = _redirect_si_pas_admin_sigaud(request)
    if denied:
        return denied
    return render(request, "admin_parametres.html", {})


@login_required
def administration_systeme(request):
    """Console type « index admin Django » (interface personnalisée Sigaeud)."""
    denied = _redirect_si_pas_admin_sigaud(request)
    if denied:
        return denied
    from django.contrib.admin.models import LogEntry

    from .constants import CORRIGE_GRATUITS_MAX

    recent_actions = (
        LogEntry.objects.filter(user=request.user)
        .select_related("content_type")
        .order_by("-action_time")[:20]
    )
    return render(
        request,
        "administration_systeme.html",
        {
            "recent_actions": recent_actions,
            "corrige_gratuits_max": CORRIGE_GRATUITS_MAX,
        },
    )


@login_required
def admin_audit_logs(request):
    """Audit logs (LogEntry comme l'admin Django)."""
    denied = _redirect_si_pas_admin_sigaud(request)
    if denied:
        return denied
    from django.contrib.admin.models import LogEntry

    logs = (
        LogEntry.objects.select_related("user", "content_type")
        .order_by("-action_time")[:200]
    )
    return render(request, "admin_audit_logs.html", {"logs": logs})


@login_required
def admin_notifications(request):
    """Centre de notifications (dernières actions admin)."""
    denied = _redirect_si_pas_admin_sigaud(request)
    if denied:
        return denied
    from django.contrib.admin.models import LogEntry

    notifications = (
        LogEntry.objects.select_related("user", "content_type")
        .order_by("-action_time")[:20]
    )
    abonnements_en_attente = (
        AbonnementEtudiant.objects.filter(statut_demande="en_attente")
        .select_related("user", "niveau_activation")
        .order_by("-date_demande")
    )
    return render(
        request,
        "admin_notifications.html",
        {
            "notifications": notifications,
            "abonnements_en_attente": abonnements_en_attente,
        },
    )


@login_required
@require_POST
def admin_valider_abonnement_etudiant(request, pk: int):
    """Valide une demande d'abonnement étudiant en attente."""
    denied = _redirect_si_pas_admin_sigaud(request)
    if denied:
        return denied
    abonnement = get_object_or_404(AbonnementEtudiant, pk=pk)
    if abonnement.statut_demande != "en_attente":
        messages.info(request, "Cette demande a déjà été traitée.")
        return redirect("admin_notifications")
    abonnement.actif = True
    abonnement.statut_demande = "approuvee"
    abonnement.date_activation = timezone.now()
    abonnement.date_traitement = timezone.now()
    abonnement.save(
        update_fields=[
            "actif",
            "statut_demande",
            "date_activation",
            "date_traitement",
            "date_mise_a_jour",
        ]
    )
    messages.success(request, f"Demande validée pour {abonnement.user.username}.")
    return redirect("admin_notifications")


@login_required
@require_POST
def admin_rejeter_abonnement_etudiant(request, pk: int):
    """Rejette une demande d'abonnement étudiant en attente."""
    denied = _redirect_si_pas_admin_sigaud(request)
    if denied:
        return denied
    abonnement = get_object_or_404(AbonnementEtudiant, pk=pk)
    if abonnement.statut_demande != "en_attente":
        messages.info(request, "Cette demande a déjà été traitée.")
        return redirect("admin_notifications")
    abonnement.actif = False
    abonnement.statut_demande = "rejetee"
    abonnement.date_traitement = timezone.now()
    abonnement.save(
        update_fields=[
            "actif",
            "statut_demande",
            "date_traitement",
            "date_mise_a_jour",
        ]
    )
    messages.warning(request, f"Demande rejetée pour {abonnement.user.username}.")
    return redirect("admin_notifications")