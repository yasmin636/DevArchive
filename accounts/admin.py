from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

admin.site.site_header = "SIGAUD — Administration système"
admin.site.site_title = "SIGAUD"
admin.site.index_title = "Administration système"

from .models import (
    AssistantPedagogique,
    ConsultationCorrigeGratuite,
    Faculte,
    Filiere,
    Niveau,
    Etudiant,
)

User = get_user_model()


class AssistantPedagogiqueInline(admin.StackedInline):
    model = AssistantPedagogique
    fk_name = "user"
    max_num = 1
    verbose_name = "Profil assistant pédagogique"
    verbose_name_plural = "Profil assistant pédagogique (une filière)"


class UserAdmin(BaseUserAdmin):
    inlines = [AssistantPedagogiqueInline]


# Remplacer l'admin User par défaut pour ajouter l'inline Assistant pédagogique
admin.site.unregister(User)
admin.site.register(User, UserAdmin)


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


@admin.register(ConsultationCorrigeGratuite)
class ConsultationCorrigeGratuiteAdmin(admin.ModelAdmin):
    list_display = ("user", "archive", "date_premier_acces")
    list_filter = ("date_premier_acces",)
    search_fields = ("user__username", "archive__title")
    raw_id_fields = ("user", "archive")


@admin.register(AssistantPedagogique)
class AssistantPedagogiqueAdmin(admin.ModelAdmin):
    list_display = ('user', 'filiere', 'created_at')
    list_filter = ('filiere',)
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'filiere__libelle')
