from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0028_abonnementetudiant_workflow_statut"),
    ]

    operations = [
        migrations.CreateModel(
            name="PaiementAbonnement",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("reference", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("provider", models.CharField(default="mastercard", max_length=40)),
                ("statut", models.CharField(choices=[("initie", "Initié"), ("en_attente", "En attente"), ("reussi", "Réussi"), ("echoue", "Échoué"), ("annule", "Annulé"), ("erreur", "Erreur")], default="initie", max_length=20)),
                ("montant_usd", models.DecimalField(decimal_places=2, default=15.0, max_digits=8)),
                ("devise", models.CharField(default="USD", max_length=10)),
                ("gateway_order_id", models.CharField(blank=True, default="", max_length=120)),
                ("gateway_session_id", models.CharField(blank=True, default="", max_length=120)),
                ("gateway_success_indicator", models.CharField(blank=True, default="", max_length=255)),
                ("payload_gateway", models.JSONField(blank=True, null=True)),
                ("message", models.TextField(blank=True, default="")),
                ("date_creation", models.DateTimeField(auto_now_add=True)),
                ("date_mise_a_jour", models.DateTimeField(auto_now=True)),
                ("date_validation", models.DateTimeField(blank=True, null=True)),
                ("abonnement", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="paiements", to="accounts.abonnementetudiant")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="paiements_abonnement", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "Paiement abonnement",
                "verbose_name_plural": "Paiements abonnement",
                "ordering": ["-date_creation"],
            },
        ),
    ]
