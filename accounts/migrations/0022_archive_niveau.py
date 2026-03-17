from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0021_telechargementetudiant"),
    ]

    operations = [
        migrations.AddField(
            model_name="archive",
            name="niveau",
            field=models.ForeignKey(
                to="accounts.niveau",
                on_delete=models.PROTECT,
                related_name="archives",
                null=True,
                blank=True,
                verbose_name="Niveau",
            ),
        ),
    ]

