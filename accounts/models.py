from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class Faculte(models.Model):
    code = models.CharField(max_length=20, unique=True)
    libelle = models.CharField(max_length=150)

    class Meta:
        verbose_name = "Faculté"
        verbose_name_plural = "Facultés"

    def __str__(self) -> str:
        return self.libelle


class Filiere(models.Model):
    code = models.CharField(max_length=20, unique=True)
    libelle = models.CharField(max_length=150)
    faculte = models.ForeignKey(
        Faculte,
        on_delete=models.PROTECT,
        related_name="filieres",
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        related_name="sous_filieres",
        null=True,
        blank=True,
        help_text="Filière parent (ex : Physique-Chimie pour Physique / Chimie).",
    )

    class Meta:
        verbose_name = "Filière"
        verbose_name_plural = "Filières"

    def __str__(self) -> str:
        if self.parent:
            return f"{self.libelle} ({self.parent.libelle})"
        return f"{self.libelle} ({self.faculte.code})"


class Niveau(models.Model):
    code = models.CharField(max_length=20, unique=True)
    libelle = models.CharField(max_length=100)
    faculte = models.ForeignKey(
        Faculte,
        on_delete=models.PROTECT,
        related_name="niveaux",
    )

    class Meta:
        verbose_name = "Niveau"
        verbose_name_plural = "Niveaux"

    def __str__(self) -> str:
        return f"{self.code} - {self.libelle}"


class AnneeAcademique(models.Model):
    code = models.CharField(max_length=20, unique=True)  # "2024-2025"
    active = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Année académique"
        verbose_name_plural = "Années académiques"

    def __str__(self) -> str:
        return self.code


class Parcours(models.Model):
    """
    Association Filière + Niveau (+ optionnellement année).
    Exemples : Physique-Chimie L1, Physique-Chimie L2, Physique L3, Chimie L3.
    """

    filiere = models.ForeignKey(
        Filiere,
        on_delete=models.PROTECT,
        related_name="parcours",
    )
    niveau = models.ForeignKey(
        Niveau,
        on_delete=models.PROTECT,
        related_name="parcours",
    )
    annee_academique = models.ForeignKey(
        AnneeAcademique,
        on_delete=models.PROTECT,
        related_name="parcours",
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = "Parcours"
        verbose_name_plural = "Parcours"
        constraints = [
            models.UniqueConstraint(
                fields=["filiere", "niveau", "annee_academique"],
                name="uniq_parcours_filiere_niveau_annee",
            )
        ]

    def __str__(self) -> str:
        if self.annee_academique:
            return f"{self.filiere.libelle} {self.niveau.code} ({self.annee_academique.code})"
        return f"{self.filiere.libelle} {self.niveau.code}"


class Etudiant(models.Model):
    """
    Profil étudiant lié au compte utilisateur Django.
    Utilisé par la page d'inscription (faculté, filière, niveau).
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="etudiant",
    )
    photo = models.ImageField(
        "Photo de profil",
        upload_to="etudiants_photos/",
        blank=True,
        null=True,
    )
    filiere = models.ForeignKey(
        Filiere,
        on_delete=models.PROTECT,
        related_name="etudiants",
    )
    niveau = models.ForeignKey(
        Niveau,
        on_delete=models.PROTECT,
        related_name="etudiants",
    )

    class Meta:
        verbose_name = "Étudiant"
        verbose_name_plural = "Étudiants"

    def __str__(self) -> str:
        return f"{self.user.get_full_name()} - {self.filiere.code} - {self.niveau.code}"


class AssistantPedagogique(models.Model):
    """
    Profil assistant pédagogique lié au compte utilisateur Django.
    Un assistant est rattaché à UNE filière et ne gère que les données de cette filière.
    Les droits sont pilotés via Groupes/Permissions Django, l'affectation filière via ce modèle.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="assistant_pedagogique",
    )
    filiere = models.ForeignKey(
        Filiere,
        on_delete=models.PROTECT,
        related_name="assistants_pedagogiques",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Assistant pédagogique"
        verbose_name_plural = "Assistants pédagogiques"

    def __str__(self) -> str:
        return f"{self.user.get_full_name() or self.user.username} — {self.filiere.code}"


GROUPE_ASSISTANT = "Assistant pédagogique"


@receiver(post_save, sender=AssistantPedagogique)
def add_assistant_to_group(sender, instance, created, **kwargs):
    """Ajoute automatiquement l'utilisateur au groupe Assistant pédagogique."""
    if created:
        from django.contrib.auth.models import Group
        group, _ = Group.objects.get_or_create(name=GROUPE_ASSISTANT)
        instance.user.groups.add(group)


class Matiere(models.Model):
    """
    Matière académique (lié à une filière).
    Correspond au modèle Matiere du MCD.
    """

    code = models.CharField(max_length=20, unique=True)
    libelle = models.CharField(max_length=150)
    filiere = models.ForeignKey(
        Filiere,
        on_delete=models.PROTECT,
        related_name="matieres",
        blank=True,
        null=True,
    )

    class Meta:
        verbose_name = "Matière"
        verbose_name_plural = "Matières"

    def __str__(self) -> str:
        return self.libelle


class TypeExamen(models.Model):
    """
    Type d'examen (CC, Examen final, Rattrapage, etc.).
    """

    libelle = models.CharField(max_length=80)

    class Meta:
        verbose_name = "Type d'examen"
        verbose_name_plural = "Types d'examen"

    def __str__(self) -> str:
        return self.libelle


class Document(models.Model):
    """
    Document physique associé à un examen (PDF scanné, énoncé, corrigé...).
    """

    nom_fichier = models.CharField(max_length=255)
    type_fichier = models.CharField(max_length=50)
    chemin_fichier = models.CharField(max_length=500)
    date_upload = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="documents_uploades",
    )

    class Meta:
        verbose_name = "Document"
        verbose_name_plural = "Documents"

    def __str__(self) -> str:
        return self.nom_fichier


class Examen(models.Model):
    """
    Examen académique (lié à une matière, un type d'examen et à un ou plusieurs parcours).
    """

    titre = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    date_publication = models.DateField(auto_now_add=True)
    matiere = models.ForeignKey(
        Matiere,
        on_delete=models.PROTECT,
        related_name="examens",
    )
    type_examen = models.ForeignKey(
        TypeExamen,
        on_delete=models.PROTECT,
        related_name="examens",
    )
    parcours = models.ManyToManyField(
        Parcours,
        related_name="examens",
        help_text="Parcours concernés par cet examen (commun ou spécifique).",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="examens_crees",
    )

    class Meta:
        verbose_name = "Examen"
        verbose_name_plural = "Examens"

    def __str__(self) -> str:
        return self.titre


class Archive(models.Model):
    """
    Vue pratique pour le tableau de bord : regroupe les métadonnées d'une
    archive + les liens vers Examen / Document et l'utilisateur qui l'a créée.
    """

    TYPE_CHOICES = [
        ("CC", "Contrôle Continu"),
        ("Examen Final", "Examen Final"),
    ]

    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    title = models.CharField("Intitulé", max_length=200)
    module = models.CharField("Module", max_length=150)
    filiere = models.CharField("Filière", max_length=150)
    niveau = models.ForeignKey(
        Niveau,
        on_delete=models.PROTECT,
        related_name="archives",
        null=True,
        blank=True,
        verbose_name="Niveau",
    )
    annee = models.CharField("Année universitaire", max_length=20)
    session = models.CharField(max_length=20, default="Normale", blank=True)
    semestre = models.CharField(max_length=10, default="S1", blank=True)
    remarque = models.TextField(blank=True)

    examen = models.ForeignKey(
        Examen,
        on_delete=models.SET_NULL,
        related_name="archives",
        blank=True,
        null=True,
    )
    fichier = models.FileField(
        upload_to="archives_pdf/",
        blank=True,
        null=True,
    )
    fichier_corrige = models.FileField(
        "Fichier corrigé (PDF)",
        upload_to="archives_corrige/",
        blank=True,
        null=True,
        help_text="Optionnel : corrigé type pour les étudiants.",
    )

    date_archive = models.DateField("Archivé le", auto_now_add=True)
    nb_vues = models.PositiveIntegerField("Nombre de vues", default=0)
    nb_telechargements = models.PositiveIntegerField("Nombre de téléchargements", default=0)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="archives_creees",
    )

    class Meta:
        verbose_name = "Archive"
        verbose_name_plural = "Archives"

    def __str__(self) -> str:
        return f"{self.title} ({self.annee})"


class NoteArchive(models.Model):
    """Note (1–5 étoiles) d'un étudiant sur une archive, une note par utilisateur."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notes_archives",
    )
    archive = models.ForeignKey(
        Archive,
        on_delete=models.CASCADE,
        related_name="notes_utilisateur",
    )
    note = models.PositiveSmallIntegerField()

    class Meta:
        verbose_name = "Note sur archive"
        verbose_name_plural = "Notes sur archives"
        unique_together = ("user", "archive")

    def __str__(self) -> str:
        return f"{self.user_id} → {self.archive_id}: {self.note}"


class ConsultationCorrigeGratuite(models.Model):
    """
    Premier accès d'un étudiant au corrigé d'une archive : compte dans la limite
    de CORRIGE_GRATUITS_MAX corrigés distincts. Les accès suivants au même corrigé
    ne créent pas de ligne supplémentaire (voir logique dans les vues).
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="corriges_gratuits_consultes",
    )
    archive = models.ForeignKey(
        Archive,
        on_delete=models.CASCADE,
        related_name="acces_corrige_gratuits",
    )
    date_premier_acces = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Accès corrigé gratuit"
        verbose_name_plural = "Accès corrigés gratuits"
        unique_together = ("user", "archive")

    def __str__(self) -> str:
        return f"{self.user_id} → archive {self.archive_id}"


class Commentaire(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="commentaires",
    )
    examen = models.ForeignKey(
        Examen,
        on_delete=models.CASCADE,
        related_name="commentaires",
    )
    contenu = models.TextField()
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Commentaire"
        verbose_name_plural = "Commentaires"
        ordering = ["-date_creation"]


class CommentaireArchive(models.Model):
    """Commentaire direct lié à une archive (sans examen)."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="commentaires_archive",
    )
    archive = models.ForeignKey(
        Archive,
        on_delete=models.CASCADE,
        related_name="commentaires_archive",
    )
    contenu = models.TextField()
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Commentaire (archive)"
        verbose_name_plural = "Commentaires (archives)"
        ordering = ["-date_creation"]


class Favori(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="favoris",
    )
    examen = models.ForeignKey(
        Examen,
        on_delete=models.CASCADE,
        related_name="favoris",
    )
    date_ajout = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Favori"
        verbose_name_plural = "Favoris"
        unique_together = ("user", "examen")


class FavoriArchive(models.Model):
    """Favori direct sur une archive (quand l'archive n'est pas liée à un examen)."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="favoris_archive",
    )
    archive = models.ForeignKey(
        Archive,
        on_delete=models.CASCADE,
        related_name="favoris_archive",
    )
    date_ajout = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Favori (archive)"
        verbose_name_plural = "Favoris (archives)"
        unique_together = ("user", "archive")


class Historique(models.Model):
    """
    Trace les consultations d'examens par les utilisateurs.
    Sert de base pour les statistiques (nb vues, examens les plus consultés, etc.).
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="historiques",
    )
    examen = models.ForeignKey(
        Examen,
        on_delete=models.CASCADE,
        related_name="historiques",
    )
    date_vue = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Historique de consultation"
        verbose_name_plural = "Historiques de consultation"
        ordering = ["-date_vue"]


class HistoriqueArchive(models.Model):
    """Historique de consultation d'une archive (sans lien examen)."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="historiques_archive",
    )
    archive = models.ForeignKey(
        Archive,
        on_delete=models.CASCADE,
        related_name="historiques_archive",
    )
    date_vue = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Historique de consultation (archive)"
        verbose_name_plural = "Historiques de consultation (archives)"
        ordering = ["-date_vue"]
        unique_together = ("user", "archive")


class Collection(models.Model):
    """Collection personnelle d'archives créée par un étudiant."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="collections",
    )
    nom = models.CharField("Nom de la collection", max_length=150)
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Collection"
        verbose_name_plural = "Collections"
        ordering = ["-date_creation"]

    def __str__(self):
        return self.nom


class CollectionArchive(models.Model):
    """Lien entre une collection et une archive."""
    collection = models.ForeignKey(
        Collection,
        on_delete=models.CASCADE,
        related_name="archives_collection",
    )
    archive = models.ForeignKey(
        Archive,
        on_delete=models.CASCADE,
        related_name="collections_archives",
    )
    date_ajout = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Archive dans une collection"
        verbose_name_plural = "Archives dans les collections"
        unique_together = ("collection", "archive")


class TelechargementEtudiant(models.Model):
    """Enregistre chaque téléchargement d'une archive par un étudiant (historique)."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="telechargements_etudiant",
    )
    archive = models.ForeignKey(
        Archive,
        on_delete=models.CASCADE,
        related_name="telechargements_etudiant",
    )
    date_telechargement = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Téléchargement étudiant"
        verbose_name_plural = "Téléchargements étudiants"
        ordering = ["-date_telechargement"]
