# Generated manually

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('accounts', '0017_etudiant_photo'),
    ]

    operations = [
        migrations.CreateModel(
            name='FavoriArchive',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_ajout', models.DateTimeField(auto_now_add=True)),
                ('archive', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='favoris_archive', to='accounts.archive')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='favoris_archive', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Favori (archive)',
                'verbose_name_plural': 'Favoris (archives)',
                'unique_together': {('user', 'archive')},
            },
        ),
    ]
