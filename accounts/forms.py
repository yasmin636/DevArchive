

from .models import AssistantPedagogique, Etudiant, Faculte, Filiere, Niveau, Archive
from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm, UserCreationForm
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, User

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
    Formulaire pour l'archivage d'un examen avec PDF (sujet) et corrigé optionnel.
    """

    class Meta:
        model = Archive
        fields = [
            "type",
            "title",
            "module",
            "niveau",
            "annee",
            "session",
            "semestre",
            "remarque",
            "fichier",
            "fichier_corrige",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["fichier"].label = "Sujet / énoncé (PDF)"
        self.fields["fichier"].help_text = (
            "Document consulté en premier par les étudiants (aperçu ou téléchargement)."
        )
        self.fields["fichier_corrige"].label = "Corrigé (PDF)"
        self.fields["fichier_corrige"].help_text = (
            "Optionnel lors de la création : les étudiants y accèdent via « Consulter correction » "
            "après avoir ouvert le sujet."
        )
        self.fields["fichier_corrige"].required = False

    def clean_fichier(self):
        f = self.cleaned_data.get("fichier")
        # En création, f est généralement un UploadedFile (avec content_type).
        # En modification sans nouvel upload, f est un FieldFile (pas de content_type).
        if f and hasattr(f, "content_type") and f.content_type != "application/pdf":
            raise forms.ValidationError("Seuls les fichiers PDF sont autorisés.")
        return f

    def clean_fichier_corrige(self):
        f = self.cleaned_data.get("fichier_corrige")
        if f and hasattr(f, "content_type") and f.content_type != "application/pdf":
            raise forms.ValidationError("Seuls les fichiers PDF sont autorisés pour le corrigé.")
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


class ProfilEtudiantForm(forms.Form):
    """Formulaire de gestion du profil étudiant : identité, faculté, filière, niveau, photo."""

    first_name = forms.CharField(
        label="Prénom",
        max_length=150,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    last_name = forms.CharField(
        label="Nom",
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    email = forms.EmailField(
        label="Adresse email",
        widget=forms.EmailInput(attrs={"class": "form-control"}),
    )
    faculte = forms.ModelChoiceField(
        label="Faculté",
        queryset=Faculte.objects.order_by("libelle"),
        widget=forms.Select(attrs={"class": "form-select", "id": "id_faculte"}),
    )
    filiere = forms.ModelChoiceField(
        label="Filière",
        queryset=Filiere.objects.none(),
        widget=forms.Select(attrs={"class": "form-select", "id": "id_filiere"}),
    )
    niveau = forms.ModelChoiceField(
        label="Niveau",
        queryset=Niveau.objects.none(),
        widget=forms.Select(attrs={"class": "form-select", "id": "id_niveau"}),
    )
    photo = forms.ImageField(
        label="Photo de profil",
        required=False,
        widget=forms.FileInput(attrs={"class": "form-control", "accept": "image/*"}),
    )
    remove_photo = forms.BooleanField(
        label="Supprimer la photo de profil",
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input", "id": "id_remove_photo"}),
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        self.etudiant = getattr(user, "etudiant", None)
        super().__init__(*args, **kwargs)
        if self.user:
            self.fields["first_name"].initial = self.user.first_name
            self.fields["last_name"].initial = self.user.last_name
            self.fields["email"].initial = self.user.email
        if self.etudiant:
            data = args[0] if args else None
            faculte_id = None
            if data and data.get("faculte"):
                try:
                    faculte_id = int(data.get("faculte"))
                except (TypeError, ValueError):
                    pass
            if faculte_id is None:
                faculte_id = self.etudiant.filiere.faculte_id
            self.fields["faculte"].initial = faculte_id
            self.fields["filiere"].queryset = Filiere.objects.filter(faculte_id=faculte_id).order_by("libelle")
            self.fields["niveau"].queryset = Niveau.objects.filter(faculte_id=faculte_id).order_by("libelle")
            self.fields["filiere"].initial = self.etudiant.filiere_id if self.etudiant.filiere.faculte_id == faculte_id else None
            self.fields["niveau"].initial = self.etudiant.niveau_id if self.etudiant.niveau.faculte_id == faculte_id else None

    def clean_email(self):
        new_email = self.cleaned_data.get("email", "").strip().lower()
        if not new_email:
            return new_email
        if User.objects.filter(email=new_email).exclude(pk=self.user.pk).exists():
            raise forms.ValidationError("Cette adresse email est déjà utilisée.")
        return new_email

    def clean(self):
        cleaned = super().clean()
        faculte = cleaned.get("faculte")
        filiere = cleaned.get("filiere")
        niveau = cleaned.get("niveau")
        if faculte:
            if filiere and filiere.faculte_id != faculte.id:
                self.add_error(
                    "filiere",
                    "La filière choisie n'appartient pas à la faculté sélectionnée. Veuillez choisir une filière de cette faculté.",
                )
            if niveau and niveau.faculte_id != faculte.id:
                self.add_error(
                    "niveau",
                    "Le niveau choisi n'appartient pas à la faculté sélectionnée. Veuillez choisir un niveau de cette faculté.",
                )
        if filiere and niveau and niveau.faculte_id != filiere.faculte_id:
            self.add_error("niveau", "Le niveau doit correspondre à la faculté de la filière choisie.")
        return cleaned

    def save(self):
        self.user.first_name = self.cleaned_data["first_name"].strip()
        self.user.last_name = self.cleaned_data["last_name"].strip()
        self.user.email = self.cleaned_data["email"].strip().lower()
        self.user.username = self.cleaned_data["email"].strip().lower()
        self.user.save(update_fields=["first_name", "last_name", "email", "username"])
        if self.etudiant:
            self.etudiant.filiere = self.cleaned_data["filiere"]
            self.etudiant.niveau = self.cleaned_data["niveau"]
            if self.cleaned_data.get("remove_photo") and self.etudiant.photo:
                self.etudiant.photo.delete(save=False)
                self.etudiant.photo = None
            elif self.cleaned_data.get("photo"):
                self.etudiant.photo = self.cleaned_data["photo"]
            self.etudiant.save()


class AdminAddUserForm(forms.Form):
    """Formulaire « Add user » pour le tableau de bord admin (style Django admin)."""
    role = forms.ChoiceField(
        choices=[
            ("etudiant", "Étudiant"),
            ("assistant", "Assistant"),
            ("admin", "Administrateur (superutilisateur)"),
        ],
        label="Type de compte",
        initial="etudiant",
        widget=forms.RadioSelect(attrs={"class": "admin-radio role-radio"}),
    )
    username = forms.CharField(
        max_length=150,
        label="Nom d'utilisateur",
        help_text="Requis. 150 caractères ou moins. Lettres, chiffres et @/./+/-/_ uniquement.",
        widget=forms.TextInput(attrs={"class": "admin-input", "autocomplete": "username"}),
    )
    email = forms.EmailField(
        label="Adresse email",
        required=True,
        widget=forms.EmailInput(attrs={"class": "admin-input", "autocomplete": "email"}),
        help_text="Adresse email de connexion (utilisée pour les notifications et la récupération du mot de passe).",
    )
    password_authentication = forms.ChoiceField(
        choices=[("enabled", "Activé"), ("disabled", "Désactivé")],
        label="Authentification par mot de passe",
        initial="enabled",
        widget=forms.RadioSelect(attrs={"class": "admin-radio"}),
    )
    password1 = forms.CharField(
        label="Mot de passe",
        strip=False,
        required=False,
        widget=forms.PasswordInput(attrs={"class": "admin-input", "autocomplete": "new-password"}),
        help_text=(
            "Votre mot de passe ne doit pas être trop proche des autres informations personnelles.<br>"
            "Votre mot de passe doit contenir au moins 8 caractères.<br>"
            "Votre mot de passe ne peut pas être un mot de passe couramment utilisé.<br>"
            "Votre mot de passe ne peut pas être entièrement numérique."
        ),
    )
    password2 = forms.CharField(
        label="Confirmation du mot de passe",
        strip=False,
        required=False,
        widget=forms.PasswordInput(attrs={"class": "admin-input", "autocomplete": "new-password"}),
        help_text="Saisissez le même mot de passe que ci-dessus, pour vérification.",
    )
    assistant_filiere = forms.ModelChoiceField(
        queryset=Filiere.objects.all().order_by("libelle"),
        label="Filière (assistant)",
        required=False,
        widget=forms.Select(attrs={"class": "admin-select"}),
        help_text="Requis pour un compte assistant.",
    )
    etudiant_faculte = forms.ModelChoiceField(
        queryset=Faculte.objects.all().order_by("libelle"),
        label="Faculté (étudiant)",
        required=False,
        widget=forms.Select(attrs={"class": "admin-select"}),
        help_text="Requis pour un compte étudiant.",
    )
    etudiant_filiere = forms.ModelChoiceField(
        queryset=Filiere.objects.all().order_by("libelle"),
        label="Filière (étudiant)",
        required=False,
        widget=forms.Select(attrs={"class": "admin-select"}),
        help_text="Requis pour un compte étudiant.",
    )
    etudiant_niveau = forms.ModelChoiceField(
        queryset=Niveau.objects.all().order_by("libelle"),
        label="Niveau (étudiant)",
        required=False,
        widget=forms.Select(attrs={"class": "admin-select"}),
        help_text="Requis pour un compte étudiant.",
    )

    def clean_username(self):
        username = self.cleaned_data.get("username", "").strip()
        User = get_user_model()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("Un utilisateur avec ce nom d'utilisateur existe déjà.")
        return username

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        User = get_user_model()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Cette adresse email est déjà utilisée.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get("role") or "etudiant"
        if cleaned_data.get("password_authentication") == "enabled":
            p1 = cleaned_data.get("password1")
            p2 = cleaned_data.get("password2")
            if not p1:
                self.add_error("password1", "Ce champ est obligatoire lorsque l'authentification par mot de passe est activée.")
            if p1 and p2 and p1 != p2:
                self.add_error("password2", "Les deux mots de passe ne correspondent pas.")
            if p1 and len(p1) < 8:
                self.add_error("password1", "Le mot de passe doit contenir au moins 8 caractères.")
        if role == "assistant":
            if not cleaned_data.get("assistant_filiere"):
                self.add_error("assistant_filiere", "Veuillez sélectionner la filière de l'assistant.")
        elif role == "etudiant":
            faculte = cleaned_data.get("etudiant_faculte")
            if not faculte:
                self.add_error("etudiant_faculte", "Veuillez sélectionner la faculté de l'étudiant.")
            if not cleaned_data.get("etudiant_filiere"):
                self.add_error("etudiant_filiere", "Veuillez sélectionner la filière de l'étudiant.")
            if not cleaned_data.get("etudiant_niveau"):
                self.add_error("etudiant_niveau", "Veuillez sélectionner le niveau de l'étudiant.")
            filiere = cleaned_data.get("etudiant_filiere")
            niveau = cleaned_data.get("etudiant_niveau")
            if faculte and filiere and filiere.faculte_id != faculte.id:
                self.add_error("etudiant_filiere", "La filière doit appartenir à la faculté sélectionnée.")
            if faculte and niveau and niveau.faculte_id != faculte.id:
                self.add_error("etudiant_niveau", "Le niveau doit appartenir à la faculté sélectionnée.")
            if filiere and niveau and filiere.faculte_id != niveau.faculte_id:
                self.add_error("etudiant_niveau", "Le niveau doit appartenir à la même faculté que la filière.")
        return cleaned_data

    def save(self):
        User = get_user_model()
        username = self.cleaned_data["username"].strip()
        email = self.cleaned_data["email"].strip().lower()
        password = self.cleaned_data.get("password1") or ""
        role = self.cleaned_data.get("role") or "etudiant"
        if self.cleaned_data.get("password_authentication") == "disabled":
            user = User.objects.create_user(username=username, email=email, password=None)
            user.set_unusable_password()
            user.save()
        else:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password or None,
            )
        if role == "admin":
            from django.contrib.auth.models import Group

            user.is_staff = True
            user.is_superuser = True
            user.save(update_fields=["is_staff", "is_superuser"])
            group, _ = Group.objects.get_or_create(name="Administrateur système")
            user.groups.add(group)
        elif role == "assistant":
            filiere = self.cleaned_data.get("assistant_filiere")
            AssistantPedagogique.objects.create(user=user, filiere=filiere)
            # Le signal add_assistant_to_group ajoute automatiquement le groupe Assistant pédagogique.
        else:
            from django.contrib.auth.models import Group

            Etudiant.objects.create(
                user=user,
                filiere=self.cleaned_data["etudiant_filiere"],
                niveau=self.cleaned_data["etudiant_niveau"],
            )
            group, _ = Group.objects.get_or_create(name="Étudiant")
            user.groups.add(group)
        return user


class AdminEditUserForm(forms.Form):
    """Edition d'un utilisateur depuis le tableau de bord admin SIGAUD."""

    username = forms.CharField(
        max_length=150,
        label="Nom d'utilisateur",
        widget=forms.TextInput(attrs={"class": "admin-input", "autocomplete": "username"}),
    )
    first_name = forms.CharField(
        max_length=150,
        label="Prénom",
        required=False,
        widget=forms.TextInput(attrs={"class": "admin-input", "autocomplete": "given-name"}),
    )
    last_name = forms.CharField(
        max_length=150,
        label="Nom",
        required=False,
        widget=forms.TextInput(attrs={"class": "admin-input", "autocomplete": "family-name"}),
    )
    email = forms.EmailField(
        label="Adresse email",
        required=False,
        widget=forms.EmailInput(attrs={"class": "admin-input", "autocomplete": "email"}),
    )
    is_active = forms.BooleanField(
        label="Compte actif",
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "admin-check"}),
    )
    is_staff = forms.BooleanField(
        label="Accès staff",
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "admin-check"}),
    )
    is_superuser = forms.BooleanField(
        label="Super administrateur",
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "admin-check"}),
    )
    groups = forms.ModelMultipleChoiceField(
        queryset=Group.objects.all().order_by("name"),
        required=False,
        label="Groupes",
        widget=forms.CheckboxSelectMultiple(attrs={"class": "admin-checklist"}),
    )
    assistant_filiere = forms.ModelChoiceField(
        queryset=Filiere.objects.all().order_by("libelle"),
        required=False,
        label="Filière assistant pédagogique",
        widget=forms.Select(attrs={"class": "admin-select"}),
    )

    def __init__(self, user_instance, *args, **kwargs):
        self.user_instance = user_instance
        super().__init__(*args, **kwargs)
        self.fields["username"].initial = user_instance.username
        self.fields["first_name"].initial = user_instance.first_name
        self.fields["last_name"].initial = user_instance.last_name
        self.fields["email"].initial = user_instance.email
        self.fields["is_active"].initial = user_instance.is_active
        self.fields["is_staff"].initial = user_instance.is_staff
        self.fields["is_superuser"].initial = user_instance.is_superuser
        self.fields["groups"].initial = user_instance.groups.all()
        assistant = getattr(user_instance, "assistant_pedagogique", None)
        if assistant:
            self.fields["assistant_filiere"].initial = assistant.filiere_id

    def clean_username(self):
        username = (self.cleaned_data.get("username") or "").strip()
        UserModel = get_user_model()
        if (
            UserModel.objects.filter(username__iexact=username)
            .exclude(pk=self.user_instance.pk)
            .exists()
        ):
            raise forms.ValidationError("Un utilisateur avec ce nom d'utilisateur existe déjà.")
        return username

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        if not email:
            return ""
        UserModel = get_user_model()
        if UserModel.objects.filter(email__iexact=email).exclude(pk=self.user_instance.pk).exists():
            raise forms.ValidationError("Cette adresse email est déjà utilisée.")
        return email

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("is_superuser"):
            cleaned["is_staff"] = True
            self.cleaned_data["is_staff"] = True
        return cleaned

    def save(self):
        u = self.user_instance
        u.username = self.cleaned_data["username"].strip()
        u.first_name = self.cleaned_data.get("first_name", "").strip()
        u.last_name = self.cleaned_data.get("last_name", "").strip()
        u.email = self.cleaned_data.get("email", "").strip().lower()
        u.is_active = bool(self.cleaned_data.get("is_active"))
        u.is_staff = bool(self.cleaned_data.get("is_staff"))
        u.is_superuser = bool(self.cleaned_data.get("is_superuser"))
        u.save()

        selected_groups = self.cleaned_data.get("groups")
        if selected_groups is not None:
            u.groups.set(selected_groups)

        assistant_group, _ = Group.objects.get_or_create(name="Assistant pédagogique")
        filiere = self.cleaned_data.get("assistant_filiere")
        assistant = getattr(u, "assistant_pedagogique", None)
        if filiere:
            if assistant:
                assistant.filiere = filiere
                assistant.save(update_fields=["filiere"])
            else:
                AssistantPedagogique.objects.create(user=u, filiere=filiere)
            u.groups.add(assistant_group)
        else:
            if assistant:
                assistant.delete()
            u.groups.remove(assistant_group)

        return u
