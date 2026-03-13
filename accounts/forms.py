

from .models import AssistantPedagogique, Etudiant, Faculte, Filiere, Niveau, Archive
from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.contrib.auth.models import User

class ConnexionForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        # 1) d'abord laisser Django initialiser le formulaire
        super().__init__(*args, **kwargs)

        # 2) ensuite on peut personnaliser les champs
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


class ArchiveForm(forms.ModelForm):
    """
    Formulaire pour l'archivage d'un examen avec PDF.
    """

    class Meta:
        model = Archive
        fields = [
            "type",
            "title",
            "module",
            "annee",
            "session",
            "semestre",
            "remarque",
            "fichier",
        ]

    def clean_fichier(self):
        f = self.cleaned_data.get("fichier")
        if f and f.content_type != "application/pdf":
            raise forms.ValidationError("Seuls les fichiers PDF sont autorisés.")
        return f


class PasswordChangeFormStyled(PasswordChangeForm):
    """Changement de mot de passe avec styles Bootstrap."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            field.widget.attrs.setdefault("class", "form-control")
            if "password" in name.lower():
                field.widget.attrs.setdefault("placeholder", "••••••••")
                field.widget.attrs.setdefault("autocomplete", "current-password" if name == "old_password" else "new-password")


class EmailChangeForm(forms.Form):
    """Changement d'adresse email (avec confirmation par mot de passe)."""

    password = forms.CharField(
        label="Mot de passe actuel",
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": "••••••••",
            "autocomplete": "current-password",
        }),
    )
    new_email = forms.EmailField(
        label="Nouvelle adresse email",
        widget=forms.EmailInput(attrs={
            "class": "form-control",
            "placeholder": "nouveau@exemple.dj",
        }),
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_password(self):
        password = self.cleaned_data.get("password")
        if password and not self.user.check_password(password):
            raise forms.ValidationError("Mot de passe incorrect.")
        return password

    def clean_new_email(self):
        new_email = self.cleaned_data.get("new_email", "").strip().lower()
        if not new_email:
            return new_email
        if User.objects.filter(email=new_email).exclude(pk=self.user.pk).exists():
            raise forms.ValidationError("Cette adresse email est déjà utilisée par un autre compte.")
        return new_email

    def save(self):
        self.user.email = self.cleaned_data["new_email"]
        self.user.username = self.cleaned_data["new_email"]
        self.user.save(update_fields=["email", "username"])


class AssistantPedagogiqueForm(forms.ModelForm):
    """
    Formulaire d'affectation d'un utilisateur à une filière comme assistant pédagogique.
    Utilisé par l'administrateur système.
    """

    user = forms.ModelChoiceField(
        label="Utilisateur",
        queryset=User.objects.filter(is_active=True).order_by("username"),
        help_text="Compte utilisateur qui deviendra assistant pédagogique.",
    )
    filiere = forms.ModelChoiceField(
        label="Filière",
        queryset=Filiere.objects.order_by("libelle"),
    )

    class Meta:
        model = AssistantPedagogique
        fields = ["user", "filiere"]

