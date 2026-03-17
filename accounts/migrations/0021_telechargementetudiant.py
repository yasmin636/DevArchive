# Generated manually

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('accounts', '0020_collection_collectionarchive'),
    ]

    operations = [
        migrations.CreateModel(
            name='TelechargementEtudiant',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_telechargement', models.DateTimeField(auto_now_add=True)),
                ('archive', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='telechargements_etudiant', to='accounts.archive')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='telechargements_etudiant', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Téléchargement étudiant',
                'verbose_name_plural': 'Téléchargements étudiants',
                'ordering': ['-date_telechargement'],
            },
        ),
    ]
