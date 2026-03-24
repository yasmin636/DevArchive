from django.contrib import admin
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.http import HttpResponseRedirect
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404
from django.urls import path, reverse
from django.utils.html import format_html

from .models import AssistantPedagogique, Faculte, Filiere, Niveau, Etudiant

User = get_user_model()


class AssistantPedagogiqueInline(admin.StackedInline):
    model = AssistantPedagogique
    fk_name = "user"
    max_num = 1
    verbose_name = "Profil assistant pédagogique"
    verbose_name_plural = "Profil assistant pédagogique (une filière)"


class UserAdmin(BaseUserAdmin):
    """
    Admin utilisateurs : plus de colonne « Staff » / statut booléen ;
    actions explicites Ajouter (réactiver), Suspendre, Modifier.
    """

    inlines = [AssistantPedagogiqueInline]

    # Retire is_staff / is_superuser / is_active des colonnes (remplacé par les boutons)
    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "actions_utilisateur",
    )
    list_display_links = ("username",)

    def changelist_view(self, request, extra_context=None):
        # Permet d’accéder à la requête dans list_display (token CSRF des mini-formulaires)
        self._dv_changelist_request = request
        try:
            return super().changelist_view(request, extra_context=extra_context)
        finally:
            self._dv_changelist_request = None

    def get_urls(self):
        info = self.model._meta.app_label, self.model._meta.model_name
        suffix_suspend = "%s_%s_devarchive_suspend" % info
        suffix_activate = "%s_%s_devarchive_activate" % info
        custom = [
            path(
                "<int:object_id>/devarchive/suspend/",
                self.admin_site.admin_view(self.user_devarchive_suspend),
                name=suffix_suspend,
            ),
            path(
                "<int:object_id>/devarchive/activate/",
                self.admin_site.admin_view(self.user_devarchive_activate),
                name=suffix_activate,
            ),
        ]
        return custom + super().get_urls()

    @admin.display(description="Actions")
    def actions_utilisateur(self, obj):
        request = getattr(self, "_dv_changelist_request", None)
        if request is None or obj.pk is None:
            return "—"

        if not request.user.has_perm("auth.change_user"):
            return "—"

        change_url = reverse("admin:auth_user_change", args=[obj.pk])
        mod_link = format_html(
            '<a class="dv-btn dv-btn-mod" href="{}">Modifier</a>',
            change_url,
        )

        token = get_token(request)
        suspend_url = reverse("admin:auth_user_devarchive_suspend", args=[obj.pk])
        activate_url = reverse("admin:auth_user_devarchive_activate", args=[obj.pk])

        peut_modérer = request.user.is_superuser or (not obj.is_superuser)
        est_moi = obj.pk == request.user.pk

        # Suspendre : compte actif, pas soi-même, et droits suffisants
        if obj.is_active and not est_moi and peut_modérer:
            suspend_block = format_html(
                '<form method="post" action="{}" class="dv-inline-form">'
                '<input type="hidden" name="csrfmiddlewaretoken" value="{}">'
                '<button type="submit" class="dv-btn dv-btn-sus">Suspendre</button></form>',
                suspend_url,
                token,
            )
        else:
            suspend_block = format_html(
                '<span class="dv-btn dv-btn-dis" title="{}">Suspendre</span>',
                "Indisponible (compte inactif, vous-même ou droits insuffisants)",
            )

        # Ajouter : réactive un compte suspendu (is_active → True)
        if not obj.is_active and not est_moi and peut_modérer:
            add_block = format_html(
                '<form method="post" action="{}" class="dv-inline-form">'
                '<input type="hidden" name="csrfmiddlewaretoken" value="{}">'
                '<button type="submit" class="dv-btn dv-btn-add">Ajouter</button></form>',
                activate_url,
                token,
            )
        else:
            add_block = format_html(
                '<span class="dv-btn dv-btn-dis" title="{}">Ajouter</span>',
                "Réactive un compte désactivé (déjà actif ou action impossible)",
            )

        return format_html(
            '<div class="dv-admin-actions">{}{}{}</div>',
            mod_link,
            suspend_block,
            add_block,
        )

    def user_devarchive_suspend(self, request, object_id):
        if request.method != "POST":
            return HttpResponseRedirect(reverse("admin:auth_user_changelist"))

        if not request.user.has_perm("auth.change_user"):
            messages.error(request, "Permission refusée.")
            return HttpResponseRedirect(reverse("admin:auth_user_changelist"))

        cible = get_object_or_404(User, pk=object_id)

        if cible.pk == request.user.pk:
            messages.error(request, "Vous ne pouvez pas suspendre votre propre compte.")
            return HttpResponseRedirect(reverse("admin:auth_user_changelist"))

        if cible.is_superuser and not request.user.is_superuser:
            messages.error(
                request,
                "Seul un super-utilisateur peut suspendre un autre super-utilisateur.",
            )
            return HttpResponseRedirect(reverse("admin:auth_user_changelist"))

        if not cible.is_active:
            messages.warning(request, "Ce compte est déjà inactif.")
            return HttpResponseRedirect(reverse("admin:auth_user_changelist"))

        cible.is_active = False
        cible.save(update_fields=["is_active"])
        messages.success(
            request,
            f"Le compte « {cible.get_username()} » a été suspendu (désactivé).",
        )
        return HttpResponseRedirect(reverse("admin:auth_user_changelist"))

    def user_devarchive_activate(self, request, object_id):
        if request.method != "POST":
            return HttpResponseRedirect(reverse("admin:auth_user_changelist"))

        if not request.user.has_perm("auth.change_user"):
            messages.error(request, "Permission refusée.")
            return HttpResponseRedirect(reverse("admin:auth_user_changelist"))

        cible = get_object_or_404(User, pk=object_id)

        if cible.pk == request.user.pk:
            messages.error(request, "Action inutile sur votre propre compte.")
            return HttpResponseRedirect(reverse("admin:auth_user_changelist"))

        if cible.is_superuser and not request.user.is_superuser:
            messages.error(request, "Permission insuffisante pour ce compte.")
            return HttpResponseRedirect(reverse("admin:auth_user_changelist"))

        if cible.is_active:
            messages.warning(request, "Ce compte est déjà actif.")
            return HttpResponseRedirect(reverse("admin:auth_user_changelist"))

        cible.is_active = True
        cible.save(update_fields=["is_active"])
        messages.success(
            request,
            f"Le compte « {cible.get_username()} » a été réactivé (Ajouter).",
        )
        return HttpResponseRedirect(reverse("admin:auth_user_changelist"))


admin.site.unregister(User)
admin.site.register(User, UserAdmin)

admin.site.site_header = "DevArchive — SIGAUD"
admin.site.site_title = "Admin DevArchive"
admin.site.index_title = "Tableau de bord"


@admin.register(Faculte)
class FaculteAdmin(admin.ModelAdmin):
    list_display = ("code", "libelle")


@admin.register(Filiere)
class FiliereAdmin(admin.ModelAdmin):
    list_display = ("code", "libelle", "faculte")


@admin.register(Niveau)
class NiveauAdmin(admin.ModelAdmin):
    list_display = ("code", "libelle", "faculte")


@admin.register(Etudiant)
class EtudiantAdmin(admin.ModelAdmin):
    list_display = ("user", "filiere", "niveau")
    list_filter = ("filiere", "niveau")


@admin.register(AssistantPedagogique)
class AssistantPedagogiqueAdmin(admin.ModelAdmin):
    list_display = ("user", "filiere", "created_at")
    list_filter = ("filiere",)
    search_fields = (
        "user__username",
        "user__first_name",
        "user__last_name",
        "filiere__libelle",
    )
