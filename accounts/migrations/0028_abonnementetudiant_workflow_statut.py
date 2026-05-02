from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0027_abonnementetudiant_niveau_activation"),
    ]

    operations = [
        migrations.AddField(
            model_name="abonnementetudiant",
            name="date_demande",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="abonnementetudiant",
            name="date_traitement",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="abonnementetudiant",
            name="statut_demande",
            field=models.CharField(
                choices=[
                    ("aucune", "Aucune"),
                    ("en_attente", "En attente"),
                    ("approuvee", "Approuvée"),
                    ("rejetee", "Rejetée"),
                ],
                default="aucune",
                max_length=20,
            ),
        ),
    ]
