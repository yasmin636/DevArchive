# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0015_archive_fichier'),
    ]

    operations = [
        migrations.AddField(
            model_name='archive',
            name='nb_vues',
            field=models.PositiveIntegerField(default=0, verbose_name='Nombre de vues'),
        ),
        migrations.AddField(
            model_name='archive',
            name='nb_telechargements',
            field=models.PositiveIntegerField(default=0, verbose_name='Nombre de téléchargements'),
        ),
    ]
