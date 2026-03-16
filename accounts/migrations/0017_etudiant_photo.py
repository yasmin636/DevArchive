# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0016_archive_nb_vues_telechargements'),
    ]

    operations = [
        migrations.AddField(
            model_name='etudiant',
            name='photo',
            field=models.ImageField(blank=True, null=True, upload_to='etudiants_photos/', verbose_name='Photo de profil'),
        ),
    ]
