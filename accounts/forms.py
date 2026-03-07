

from .models import Etudiant, Faculte, Filiere, Niveau
from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User

class ConnexionForm(AuthenticationForm):
    """Formulaire de connexion : email = username (comme à l'inscription)."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "Adresse électronique"
        self.fields["username"].widget.attrs.update({
            "class": "form-control",
            "placeholder": "nom@gmail.com",
            "autocomplete": "email",
        })
        self.fields["password"].widget.attrs.update({
            "class": "form-control",
            "placeholder": "••••••••",
            "autocomplete": "current-password",
        })

class EtudiantRegistrationForm(forms.Form):
    full_name = forms.CharField(
        label="Nom complet",
        max_length=150,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Ex: Ahmed Abdourahman",
            }
        ),
    )
    email = forms.EmailField(
        label="Email universitaire",
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
                "placeholder": "prenom.nom@gmail.com",
            }
        ),
    )
    faculte = forms.ModelChoiceField(
        label="Faculté",
        queryset=Faculte.objects.all(),
        widget=forms.Select(
            attrs={
                "class": "form-select",
            }
        ),
    )
    niveau = forms.ModelChoiceField(
        label="Niveau",
        queryset=Niveau.objects.all(),
        widget=forms.Select(
            attrs={
                "class": "form-select",
            }
        ),
    )
    filiere = forms.ModelChoiceField(
        label="Filière",
        queryset=Filiere.objects.all(),
        widget=forms.Select(
            attrs={
                "class": "form-select",
            }
        ),
    )
    password1 = forms.CharField(
        label="Mot de passe",
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "••••••••",
            }
        ),
    )
    password2 = forms.CharField(
        label="Confirmer le mot de passe",
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "••••••••",
            }
        ),
    )

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Un compte avec cet email existe déjà.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        pwd1 = cleaned_data.get("password1")
        pwd2 = cleaned_data.get("password2")
        if pwd1 and pwd2 and pwd1 != pwd2:
            self.add_error("password2", "Les mots de passe ne correspondent pas.")

        faculte = cleaned_data.get("faculte")
        filiere = cleaned_data.get("filiere")
        niveau = cleaned_data.get("niveau")
        if faculte and filiere and filiere.faculte_id != faculte.id:
            self.add_error(
                "filiere",
                "Cette filière n'appartient pas à la faculté sélectionnée.",
            )
        if faculte and niveau and niveau.faculte_id != faculte.id:
            self.add_error(
                "niveau",
                "Ce niveau n'appartient pas à la faculté sélectionnée.",
            )
        return cleaned_data

    def save(self):
        """
        Crée un utilisateur Django + le profil Étudiant associé.
        Utilise l'email comme username.
        """

        from django.contrib.auth.models import User

        full_name = self.cleaned_data["full_name"].strip()
        first_name = full_name.split(" ", 1)[0]
        last_name = ""
        if " " in full_name:
            last_name = full_name.split(" ", 1)[1]

        email = self.cleaned_data["email"].lower()
        password = self.cleaned_data["password1"]

        user = User.objects.create_user(
            username=email,
            email=email,
            first_name=first_name,
            last_name=last_name,
            password=password,
        )

        Etudiant.objects.create(
            user=user,
            filiere=self.cleaned_data["filiere"],
            niveau=self.cleaned_data["niveau"],
        )

        return user

