from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0022_archive_niveau"),
    ]

    operations = [
        migrations.CreateModel(
            name="CommentaireArchive",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("contenu", models.TextField()),
                ("date_creation", models.DateTimeField(auto_now_add=True)),
                (
                    "archive",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE,
                        related_name="commentaires_archive",
                        to="accounts.archive",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE,
                        related_name="commentaires_archive",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Commentaire (archive)",
                "verbose_name_plural": "Commentaires (archives)",
                "ordering": ["-date_creation"],
            },
        ),
    ]

