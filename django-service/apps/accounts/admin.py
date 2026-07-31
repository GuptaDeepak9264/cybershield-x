from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CyberShieldUserAdmin(UserAdmin):
    list_display = ("username", "email", "role", "is_staff", "is_active", "created_at")
    list_filter = ("role", "is_staff", "is_active")
    search_fields = ("username", "email")
    ordering = ("-created_at",)

    fieldsets = UserAdmin.fieldsets + (
        ("CyberShield X", {"fields": ("role", "organization")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("CyberShield X", {"fields": ("email", "role", "organization")}),
    )
