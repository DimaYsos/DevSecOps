from django.core.exceptions import PermissionDenied


def is_sys_admin(user):
    return bool(getattr(user, "is_authenticated", False) and getattr(user, "role", "") == "sys_admin")


def is_org_admin(user):
    return bool(getattr(user, "is_authenticated", False) and getattr(user, "role", "") in {"org_admin", "sys_admin"})


def scope_queryset(queryset, user, org_lookup="organization"):
    if not getattr(user, "is_authenticated", False):
        return queryset.none()
    if is_sys_admin(user):
        return queryset
    org_id = getattr(user, "organization_id", None)
    if not org_id:
        return queryset.none()
    return queryset.filter(**{f"{org_lookup}_id": org_id})


def require_same_org_or_admin(user, organization_id):
    if is_sys_admin(user):
        return
    if not getattr(user, "is_authenticated", False) or getattr(user, "organization_id", None) != organization_id:
        raise PermissionDenied("You do not have permission to access this resource.")
