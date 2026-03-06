from django.contrib import admin
from .models import Faculte, Filiere, Niveau, Etudiant


@admin.register(Faculte)
class FaculteAdmin(admin.ModelAdmin):
    list_display = ('code', 'libelle')


@admin.register(Filiere)
class FiliereAdmin(admin.ModelAdmin):
    list_display = ('code', 'libelle', 'faculte')


@admin.register(Niveau)
class NiveauAdmin(admin.ModelAdmin):
    list_display = ('code', 'libelle', 'faculte')


@admin.register(Etudiant)
class EtudiantAdmin(admin.ModelAdmin):
    list_display = ('user', 'filiere', 'niveau')
    list_filter = ('filiere', 'niveau')
