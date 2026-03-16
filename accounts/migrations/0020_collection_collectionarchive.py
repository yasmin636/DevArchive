# Generated manually

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('accounts', '0019_historiquearchive'),
    ]

    operations = [
        migrations.CreateModel(
            name='Collection',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nom', models.CharField(max_length=150, verbose_name='Nom de la collection')),
                ('date_creation', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='collections', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Collection',
                'verbose_name_plural': 'Collections',
                'ordering': ['-date_creation'],
            },
        ),
        migrations.CreateModel(
            name='CollectionArchive',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_ajout', models.DateTimeField(auto_now_add=True)),
                ('archive', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='collections_archives', to='accounts.archive')),
                ('collection', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='archives_collection', to='accounts.collection')),
            ],
            options={
                'verbose_name': 'Archive dans une collection',
                'verbose_name_plural': 'Archives dans les collections',
                'unique_together': {('collection', 'archive')},
            },
        ),
    ]
