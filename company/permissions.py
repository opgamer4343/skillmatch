from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseForbidden


def user_is_company(user):
    return user.is_authenticated and getattr(user, "role", None) == "company"


def company_required(view_func):
    @login_required
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not user_is_company(request.user):
            raise PermissionDenied("You do not have permission to access this page.")
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def company_required_response(view_func):
    @login_required
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not user_is_company(request.user):
            return HttpResponseForbidden("Company access only.")
        return view_func(request, *args, **kwargs)
    return _wrapped_view
