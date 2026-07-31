from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def role_required(*allowed_roles):
    """
    Restrict a view to users whose `role` is in allowed_roles.

    Stacked on top of login_required so an anonymous request gets sent to
    the login page (not a 403), while an authenticated user with the wrong
    role gets a hard 403 - we don't want students probing admin URLs to
    learn anything from the response.
    """

    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped(request, *args, **kwargs):
            if request.user.role not in allowed_roles:
                raise PermissionDenied("You do not have access to this resource.")
            return view_func(request, *args, **kwargs)

        return _wrapped

    return decorator


student_required = role_required("STUDENT")
admin_required = role_required("ADMIN")
