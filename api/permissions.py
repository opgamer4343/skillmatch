from rest_framework.permissions import BasePermission


class IsStudent(BasePermission):
    """
    Allows access only to authenticated student users.
    """
    message = "Only students can access this endpoint."

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and getattr(user, "role", None) == "student")


class IsCompany(BasePermission):
    """
    Allows access only to authenticated company users.
    """
    message = "Only company users can access this endpoint."

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and getattr(user, "role", None) == "company")
