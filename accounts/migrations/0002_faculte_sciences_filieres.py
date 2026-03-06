# Migration de données : Faculté des Sciences et ses filières

from django.db import migrations


def add_faculte_sciences(apps, schema_editor):
    Faculte = apps.get_model("accounts", "Faculte")
    Filiere = apps.get_model("accounts", "Filiere")
    Niveau = apps.get_model("accounts", "Niveau")

    fac, _ = Faculte.objects.get_or_create(
        code="FS",
        defaults={"libelle": "Faculté des Sciences"},
    )

    filieres_sciences = [
        ("INFO", "Informatique"),
        ("MATH", "Mathématique"),
        ("PHYS", "Physique-chimie"),
        ("BIO", "Biologie"),
    ]
    for code, libelle in filieres_sciences:
        Filiere.objects.get_or_create(
            code=code,
            defaults={"libelle": libelle, "faculte": fac},
        )

    # Niveaux courants pour la faculté (pour que l'inscription fonctionne)
    niveaux = [
        ("L1", "Licence 1"),
        ("L2", "Licence 2"),
        ("L3", "Licence 3"),
        ("M1", "Master 1"),
        ("M2", "Master 2"),
    ]
    for code, libelle in niveaux:
        Niveau.objects.get_or_create(
            code=code,
            defaults={"libelle": libelle, "faculte": fac},
        )


def remove_faculte_sciences(apps, schema_editor):
    Faculte = apps.get_model("accounts", "Faculte")
    Faculte.objects.filter(code="FS").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(add_faculte_sciences, remove_faculte_sciences),
    ]
