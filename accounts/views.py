from django.contrib import messages
from django.shortcuts import redirect, render

from .forms import EtudiantRegistrationForm
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
            return redirect("inscription")
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

