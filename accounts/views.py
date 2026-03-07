from django.contrib import messages
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render
from django.urls import reverse_lazy

from .forms import ConnexionForm, EtudiantRegistrationForm
from .models import Filiere, Niveau


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


class ConnexionView(LoginView):
    """Page de connexion (email + mot de passe). Affiche toujours la page en GET."""
    template_name = "Connexion.html"
    authentication_form = ConnexionForm
    redirect_authenticated_user = False

    def dispatch(self, request, *args, **kwargs):
        # Forcer l'affichage de la page de connexion (jamais de 302 en GET)
        if request.method == "GET":
            self.redirect_authenticated_user = False
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse_lazy("inscription")