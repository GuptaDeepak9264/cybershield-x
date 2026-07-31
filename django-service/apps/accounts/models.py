from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom auth user for CyberShield X.

    We extend AbstractUser instead of writing a user model from scratch -
    Django's built-in password hashing, permission plumbing, and admin
    integration are battle-tested and there's no reason to reinvent them.
    We only add what the domain actually needs: a role and a unique email.

    FastAPI and Flask (added in later milestones) will read this same
    table for identity checks, so the schema here is the single source of
    truth for "who is this user and what can they do".
    """

    class Role(models.TextChoices):
        STUDENT = "STUDENT", "Student"
        ADMIN = "ADMIN", "Admin"

    email = models.EmailField(unique=True)
    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.STUDENT,
        help_text="Drives dashboard routing and permission checks.",
    )
    organization = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "accounts_user"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.username} ({self.role})"

    @property
    def is_student(self) -> bool:
        return self.role == self.Role.STUDENT

    @property
    def is_admin_role(self) -> bool:
        # Named is_admin_role (not is_admin) to avoid any confusion with
        # Django's own is_staff/is_superuser flags, which control the
        # separate /admin/ site and are intentionally NOT tied to this role.
        return self.role == self.Role.ADMIN
