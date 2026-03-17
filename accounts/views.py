from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import LoginView, LogoutView
<<<<<<< HEAD
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
=======
from django.contrib.auth.tokens import default_token_generator
from django.db import models
from django.db.utils import ProgrammingError
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.core.mail import send_mail
>>>>>>> page-utilisateur-fonctionnel
from django.views.generic import TemplateView

from .forms import (
    ArchiveForm,
    ConnexionForm,
    EmailChangeForm,
    EtudiantRegistrationForm,
    PasswordChangeFormStyled,
<<<<<<< HEAD
)
from .models import Archive, AssistantPedagogique, Filiere, Niveau
=======
    ProfilEtudiantForm,
)
from .models import (
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
    TelechargementEtudiant,
)
>>>>>>> page-utilisateur-fonctionnel

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


<<<<<<< HEAD
=======
def user_est_etudiant(user):
    """True si l'utilisateur a un profil Étudiant (et pas assistant/admin)."""
    if not user.is_authenticated:
        return False
    if user_est_assistant(user):
        return False
    return hasattr(user, "etudiant") and user.etudiant is not None


>>>>>>> page-utilisateur-fonctionnel
class PersonnelRequiredMixin(UserPassesTestMixin):
    """
    Mixin qui restreint l'accès à l'espace personnel aux assistants pédagogiques
    (et admins système via staff/superuser ou groupe).
    """
    login_url = "connexion"

    def test_func(self):
        return user_est_assistant(self.request.user)
<<<<<<< HEAD
=======


class EtudiantRequiredMixin(UserPassesTestMixin):
    """Mixin qui restreint l'accès à l'espace étudiant aux utilisateurs avec profil Étudiant."""
    login_url = "connexion"

    def test_func(self):
        return user_est_etudiant(self.request.user)
>>>>>>> page-utilisateur-fonctionnel


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
            user = form.save()
            # Le compte reste inactif tant que l'email n'est pas confirmé
            user.is_active = False
            user.save(update_fields=["is_active"])

            # Envoi de l'email de confirmation
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            confirm_url = request.build_absolute_uri(
                reverse("confirmer_email", args=[uid, token])
            )
            sujet = "Confirmez votre adresse email - DevArchive"
            message = (
                "Bonjour,\n\n"
                "Vous venez de créer un compte sur DevArchive avec cette adresse email.\n"
                "Pour confirmer que cette adresse existe bien et vous appartient, cliquez sur le lien ci-dessous :\n\n"
                f"{confirm_url}\n\n"
                "Si vous n'êtes pas à l'origine de cette inscription, vous pouvez ignorer ce message.\n\n"
                "Cordialement,\n"
                "L'équipe DevArchive"
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
                "Cliquez sur le lien dans ce mail pour activer votre compte.",
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


<<<<<<< HEAD
=======
def confirmer_email(request, uidb64, token):
    """
    Active le compte après clic sur le lien reçu par email.
    """
    from django.contrib.auth.models import User

    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        if not user.is_active:
            user.is_active = True
            user.save(update_fields=["is_active"])
        messages.success(
            request,
            "Votre adresse email a été confirmée. Vous pouvez maintenant vous connecter.",
        )
        return redirect("connexion")

    messages.error(
        request,
        "Le lien de confirmation est invalide ou a déjà été utilisé.",
    )
    return redirect("inscription")

>>>>>>> page-utilisateur-fonctionnel
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
        2. tableau de bord admin si staff/superuser
        3. espace personnel si assistant pédagogique
        4. espace étudiant si étudiant
        5. sinon page d'inscription
        """
        url = self.get_redirect_url()
        if url:
            return url
        if self.request.user.is_staff or self.request.user.is_superuser:
            return reverse_lazy("admin_dashboard")
        if user_est_assistant(self.request.user):
            return reverse_lazy("personnel")
<<<<<<< HEAD
=======
        if user_est_etudiant(self.request.user):
            return reverse_lazy("espace_etudiant")
>>>>>>> page-utilisateur-fonctionnel
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


<<<<<<< HEAD
=======
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


class EspaceEtudiantView(EtudiantRequiredMixin, LoginRequiredMixin, TemplateView):
    """
    Tableau de bord étudiant : sujets de sa filière, recherche, historique.
    """
    template_name = "etudiant.html"
    login_url = "connexion"

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
        ctx["sujets_plus_visites"] = archives[:8]
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
    return render(
        request,
        "etudiant_favoris.html",
        {
            "etudiant": etudiant,
            "faculte": etudiant.filiere.faculte,
            "favoris": items,
        },
    )


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
    return render(
        request,
        "etudiant_collection_detail.html",
        {
            "collection": collection,
            "archives_in_collection": archives_in_collection,
            "archives_disponibles": archives_disponibles,
            "matieres_list": matieres_list,
            "matiere_choisie": matiere_choisie,
        },
    )


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


>>>>>>> page-utilisateur-fonctionnel
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


<<<<<<< HEAD
=======
@login_required
def voir_archive_pdf_etudiant(request, pk: int):
    """Permet à un étudiant de consulter le PDF dans le navigateur. nb_vues n'est incrémenté qu'une seule fois par utilisateur (première consultation)."""
    if not user_est_etudiant(request.user):
        raise Http404()
    qs = _archives_queryset_for_etudiant(request)
    archive = get_object_or_404(qs, pk=pk)
    if not archive.fichier:
        raise Http404("Aucun fichier associé.")
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


>>>>>>> page-utilisateur-fonctionnel
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


@login_required
def admin_dashboard(request):
    """Tableau de bord Sigaud : réservé staff/superuser, données comme admin.py."""
    if not (request.user.is_staff or request.user.is_superuser):
        messages.warning(request, "Accès réservé aux administrateurs.")
        return redirect("accueil")
    from django.contrib.auth import get_user_model
    from django.db.models import Count
    from django.contrib.admin.models import LogEntry

    User = get_user_model()
    total_users = User.objects.count()
    total_assistants = AssistantPedagogique.objects.count()
    total_archives = Archive.objects.count()
    recent_users = User.objects.order_by("-date_joined")[:5]

    # Activité récente : dernières actions admin (LogEntry)
    log_entries = (
        LogEntry.objects.select_related("user", "content_type")
        .order_by("-action_time")[:10]
    )
    action_labels = {
        1: "Ajout",
        2: "Modification",
        3: "Suppression",
    }
    model_labels = {
        "user": "utilisateur",
        "archive": "document / examen",
        "assistantpedagogique": "assistant pédagogique",
        "faculte": "faculté",
        "filiere": "filière",
        "niveau": "niveau",
        "etudiant": "étudiant",
        "group": "groupe",
    }
    recent_activity = []
    for log in log_entries:
        model_name = (log.content_type.model if log.content_type else "").lower()
        model_label = model_labels.get(model_name, model_name or "élément")
        action = action_labels.get(log.action_flag, f"Action {log.action_flag}")
        if log.action_flag == 1:
            if model_name == "assistantpedagogique":
                label = "Nouvel assistant pédagogique créé"
            elif model_name == "archive":
                label = "Nouvel examen / document ajouté"
            else:
                label = f"Nouveau {model_label} ajouté"
        elif log.action_flag == 2:
            label = f"{model_label.capitalize()} modifié"
        elif log.action_flag == 3:
            if model_name == "archive":
                label = "Document / examen supprimé"
            else:
                label = f"{model_label.capitalize()} supprimé"
        else:
            label = f"{action} – {model_label}"
        user_name = log.user.get_full_name().strip() or log.user.username if log.user else "—"
        recent_activity.append({
            "label": label,
            "object_repr": log.object_repr[:80] if log.object_repr else "",
            "user_name": user_name,
            "time_ago": _format_activity_ago(log.action_time),
        })

    return render(
        request,
        "admin.html",
        {
            "total_users": total_users,
            "total_assistants": total_assistants,
            "total_archives": total_archives,
            "recent_users": recent_users,
            "recent_activity": recent_activity,
        },
    )


@login_required
def admin_utilisateurs(request):
    """Liste des utilisateurs avec recherche et filtres (style Django admin)."""
    if not (request.user.is_staff or request.user.is_superuser):
        messages.warning(request, "Accès réservé aux administrateurs.")
        return redirect("accueil")
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
    groups = Group.objects.all().order_by("name")

    return render(
        request,
        "admin_utilisateurs.html",
        {
            "users": users,
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
    if not (request.user.is_staff or request.user.is_superuser):
        messages.warning(request, "Accès réservé aux administrateurs.")
        return redirect("accueil")
    from .forms import AdminAddUserForm

    form = AdminAddUserForm()
    if request.method == "POST":
        form = AdminAddUserForm(request.POST)
        if form.is_valid():
            new_user = form.save()
            messages.success(request, f"L'utilisateur « {new_user.username } » a été créé.")
            action = request.POST.get("_action", "save")
            if action == "add_another":
                return redirect("admin_add_user")
            if action == "continue":
                from django.urls import reverse
                try:
                    return redirect("admin:auth_user_change", new_user.pk)
                except Exception:
                    return redirect("admin_utilisateurs")
            return redirect("admin_utilisateurs")
    return render(request, "admin_add_user.html", {"form": form})


@login_required
def admin_documents(request):
    """Liste des archives/documents (données comme admin)."""
    if not (request.user.is_staff or request.user.is_superuser):
        messages.warning(request, "Accès réservé aux administrateurs.")
        return redirect("accueil")
    documents = Archive.objects.all().order_by("-date_archive")
    return render(request, "admin_documents.html", {"documents": documents})


@login_required
def admin_statistiques(request):
    """Statistiques sur les archives (agrégats)."""
    if not (request.user.is_staff or request.user.is_superuser):
        messages.warning(request, "Accès réservé aux administrateurs.")
        return redirect("accueil")
    from django.db.models import Count

    total_archives = Archive.objects.count()
    stats_par_annee = (
        Archive.objects.values("annee")
        .annotate(nb=Count("id"))
        .order_by("-annee")[:10]
    )
    stats_par_type = (
        Archive.objects.values("type").annotate(nb=Count("id")).order_by("-nb")
    )
    stats_par_filiere = (
        Archive.objects.values("filiere")
        .annotate(nb=Count("id"))
        .order_by("-nb")[:10]
    )
    return render(
        request,
        "admin_statistiques.html",
        {
            "total_archives": total_archives,
            "stats_par_annee": stats_par_annee,
            "stats_par_type": stats_par_type,
            "stats_par_filiere": stats_par_filiere,
        },
    )


@login_required
def admin_facultes(request):
    """Liste des facultés (comme admin.py Facultés)."""
    if not (request.user.is_staff or request.user.is_superuser):
        messages.warning(request, "Accès réservé aux administrateurs.")
        return redirect("accueil")
    from django.db.models import Count

    facultes = Faculte.objects.annotate(nb_filieres=Count("filieres")).order_by("code")
    return render(request, "admin_facultes.html", {"facultes": facultes})


@login_required
def admin_parametres(request):
    """Page paramètres : lien vers l'admin Django."""
    if not (request.user.is_staff or request.user.is_superuser):
        messages.warning(request, "Accès réservé aux administrateurs.")
        return redirect("accueil")
    return render(request, "admin_parametres.html", {})


@login_required
def admin_audit_logs(request):
    """Audit logs (LogEntry comme l'admin Django)."""
    if not (request.user.is_staff or request.user.is_superuser):
        messages.warning(request, "Accès réservé aux administrateurs.")
        return redirect("accueil")
    from django.contrib.admin.models import LogEntry

    logs = (
        LogEntry.objects.select_related("user", "content_type")
        .order_by("-action_time")[:200]
    )
    return render(request, "admin_audit_logs.html", {"logs": logs})


@login_required
def admin_notifications(request):
    """Centre de notifications (dernières actions admin)."""
    if not (request.user.is_staff or request.user.is_superuser):
        messages.warning(request, "Accès réservé aux administrateurs.")
        return redirect("accueil")
    from django.contrib.admin.models import LogEntry

    notifications = (
        LogEntry.objects.select_related("user", "content_type")
        .order_by("-action_time")[:20]
    )
    return render(request, "admin_notifications.html", {"notifications": notifications})