# Migration pour créer le groupe "Personnel" (assignable lors de la création d'un utilisateur dans l'admin)

from django.db import migrations


def create_groupe_personnel(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    if not Group.objects.filter(name="Personnel").exists():
        Group.objects.create(name="Personnel")


def remove_groupe_personnel(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.filter(name="Personnel").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0009_remove_administration_niveau_accreditation_and_more"),
    ]

    operations = [
        migrations.RunPython(create_groupe_personnel, remove_groupe_personnel),
    ]
