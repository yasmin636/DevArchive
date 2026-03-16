# Generated manually

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('accounts', '0018_favoriarchive'),
    ]

    operations = [
        migrations.CreateModel(
            name='HistoriqueArchive',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_vue', models.DateTimeField(auto_now_add=True)),
                ('archive', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='historiques_archive', to='accounts.archive')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='historiques_archive', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Historique de consultation (archive)',
                'verbose_name_plural': 'Historiques de consultation (archives)',
                'ordering': ['-date_vue'],
                'unique_together': {('user', 'archive')},
            },
        ),
    ]
