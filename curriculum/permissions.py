# permissions.py
from rest_framework import permissions

class IsAdminOrOwnProfile(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        # Se o usuário for admin, ele tem permissão total
        if request.user.is_staff:
            return True
        # Caso contrário, o usuário só pode acessar seu próprio perfil
        return obj == request.user
