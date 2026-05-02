from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0025_consultation_corrige_gratuite"),
    ]

    operations = [
        migrations.CreateModel(
            name="AbonnementEtudiant",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("actif", models.BooleanField(default=False)),
                ("montant_usd", models.DecimalField(decimal_places=2, default=15.0, max_digits=8)),
                ("date_activation", models.DateTimeField(blank=True, null=True)),
                ("date_mise_a_jour", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="abonnement_etudiant",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Abonnement étudiant",
                "verbose_name_plural": "Abonnements étudiants",
            },
        ),
    ]
