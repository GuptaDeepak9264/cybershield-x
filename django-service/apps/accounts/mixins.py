from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin

from .models import User


class RoleRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    Class-based-view counterpart to accounts.decorators.role_required.

    Kept in the accounts app (not duplicated per-app) so "who can do what"
    has exactly one home, whether the view is a function or a class.
    """

    allowed_roles: tuple[str, ...] = ()

    def test_func(self):
        return self.request.user.role in self.allowed_roles

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied("You do not have access to this resource.")


class AdminRequiredMixin(RoleRequiredMixin):
    allowed_roles = (User.Role.ADMIN,)


class StudentRequiredMixin(RoleRequiredMixin):
    allowed_roles = (User.Role.STUDENT,)
