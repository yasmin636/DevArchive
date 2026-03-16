from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import AssistantPedagogique, Faculte, Filiere, Niveau, Etudiant

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


@admin.register(AssistantPedagogique)
class AssistantPedagogiqueAdmin(admin.ModelAdmin):
    list_display = ('user', 'filiere', 'created_at')
    list_filter = ('filiere',)
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'filiere__libelle')
