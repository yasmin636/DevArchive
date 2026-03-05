from django.conf import settings
from django.db import models


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

    class Meta:
        verbose_name = "Filière"
        verbose_name_plural = "Filières"

    def __str__(self) -> str:
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

