from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0026_abonnementetudiant"),
    ]

    operations = [
        migrations.AddField(
            model_name="abonnementetudiant",
            name="niveau_activation",
            field=models.ForeignKey(
                blank=True,
                help_text="Niveau de l'étudiant au moment de l'activation de l'abonnement.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="abonnements_etudiants",
                to="accounts.niveau",
            ),
        ),
    ]
