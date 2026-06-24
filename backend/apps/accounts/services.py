"""Lógica de negocio de auth (F1).

Emisión, rotación y revocación de tokens + cambio de contraseña propio. La lógica vive
aquí, no en las vistas (vistas delgadas). Las cookies del refresh se setean/limpian aquí
porque son parte de la transición de sesión.

`revoke_all_refresh(user)` es un helper REUTILIZABLE: F3 (user-management) lo necesita en
el reset administrativo, la desactivación y el cambio de perfil. `change_own_password`
DELEGA en él en lugar de reimplementar la invalidación por usuario (DRY).
"""

from __future__ import annotations

import secrets
import string
from datetime import timedelta
from typing import Any, cast

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser
from django.db import transaction
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)
from rest_framework_simplejwt.tokens import RefreshToken

from apps.authz.catalog import role_for_profile_name
from apps.authz.models import Profile
from apps.common.audit import audit

from .models import User


def _set_refresh_cookie(response: Response, raw_refresh: str) -> None:
    """Setea el refresh token como cookie httpOnly con los atributos del entorno."""
    lifetime = cast(timedelta, settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"])
    response.set_cookie(
        key=settings.AUTH_COOKIE_NAME,
        value=raw_refresh,
        max_age=int(lifetime.total_seconds()),
        httponly=settings.AUTH_COOKIE_HTTPONLY,
        secure=settings.AUTH_COOKIE_SECURE,
        samesite=cast(Any, settings.AUTH_COOKIE_SAMESITE),
        path=settings.AUTH_COOKIE_PATH,
        domain=settings.AUTH_COOKIE_DOMAIN,
    )


def _clear_refresh_cookie(response: Response) -> None:
    """Elimina la cookie de refresh (logout / refresh inválido)."""
    response.delete_cookie(
        key=settings.AUTH_COOKIE_NAME,
        path=settings.AUTH_COOKIE_PATH,
        domain=settings.AUTH_COOKIE_DOMAIN,
        samesite=cast(Any, settings.AUTH_COOKIE_SAMESITE),
    )


def issue_tokens(user: AbstractBaseUser, response: Response) -> str:
    """Emite un par de tokens: access (devuelto, va en el cuerpo) + refresh en cookie."""
    refresh = RefreshToken.for_user(user)
    _set_refresh_cookie(response, str(refresh))
    return str(refresh.access_token)


def rotate_refresh(raw_refresh: str | None, response: Response) -> str:
    """Rota el refresh: valida el actual, lo agrega a la blacklist y emite uno nuevo.

    Devuelve un nuevo access. Un refresh ausente, expirado o revocado produce 401.
    """
    if not raw_refresh:
        raise InvalidToken("No se encontró la sesión. Inicie sesión nuevamente.")
    try:
        old = RefreshToken(cast(Any, raw_refresh))  # valida firma, expiración y blacklist
    except TokenError as exc:
        raise InvalidToken("La sesión expiró o no es válida. Inicie sesión nuevamente.") from exc

    claim = str(settings.SIMPLE_JWT.get("USER_ID_CLAIM", "user_id"))
    user_id = old.get(claim)
    with transaction.atomic():
        old.blacklist()
        user = User.objects.get(pk=user_id)
        new = RefreshToken.for_user(user)
        _set_refresh_cookie(response, str(new))
    return str(new.access_token)


def revoke_refresh(raw_refresh: str | None, response: Response) -> None:
    """Cierra sesión: blacklist del refresh de la cookie y limpia la cookie (idempotente)."""
    with transaction.atomic():
        if raw_refresh:
            try:
                RefreshToken(cast(Any, raw_refresh)).blacklist()
            except TokenError:
                # Ya estaba revocado/expirado: el logout es idempotente, solo limpiamos.
                pass
        _clear_refresh_cookie(response)


def revoke_all_refresh(user: User) -> None:
    """Blacklist de TODOS los refresh vigentes del usuario. Helper reutilizable (F3)."""
    with transaction.atomic():
        for token in OutstandingToken.objects.filter(user=user):
            BlacklistedToken.objects.get_or_create(token=token)


def change_own_password(user: User, current_password: str, new_password: str) -> None:
    """Cambia la contraseña propia: valida la actual, aplica la nueva e invalida sesiones.

    La política de la nueva contraseña ya la validó el serializer. Aquí se verifica la
    actual y se delega la invalidación de sesiones en `revoke_all_refresh`.
    """
    if not user.check_password(current_password):
        raise serializers.ValidationError(
            {"current_password": ["La contraseña actual es incorrecta."]}
        )
    with transaction.atomic():
        user.set_password(new_password)
        # F3: un cambio propio exitoso satisface la obligación del reset administrativo.
        user.must_change_password = False
        user.save(update_fields=["password", "must_change_password"])
        revoke_all_refresh(user)


# --- Administración de usuarios (F3 user-management) --------------------------


def _sync_role_to_profile(target: User, profile: Profile) -> None:
    """Sincroniza el `role` nominal con el perfil semilla; los perfiles a medida no lo tocan."""
    role = role_for_profile_name(profile.name)
    if role is not None:
        target.role = role


def generate_temporary_password() -> str:
    """Genera una contraseña temporal robusta (cumple la política de Django)."""
    alphabet = string.ascii_letters + string.digits
    # 14 caracteres con al menos una minúscula, una mayúscula y un dígito.
    while True:
        candidate = "".join(secrets.choice(alphabet) for _ in range(14))
        if (
            any(c.islower() for c in candidate)
            and any(c.isupper() for c in candidate)
            and any(c.isdigit() for c in candidate)
        ):
            return candidate


@audit(action="CREATE", entity="User")
def create_user(
    *,
    user: User,
    username: str,
    password: str,
    profile: Profile,
    first_name: str = "",
    last_name: str = "",
) -> User:
    """Crea un usuario con su perfil y el `role` sincronizado. `user` es el actor (auditoría)."""
    with transaction.atomic():
        target = User(
            username=username, first_name=first_name, last_name=last_name, profile=profile
        )
        _sync_role_to_profile(target, profile)
        target.set_password(password)
        target.save()
    return target


@audit(action="UPDATE", entity="User")
def update_user(*, user: User, target: User, first_name: str, last_name: str) -> User:
    """Edita los datos básicos del usuario. `user` es el actor (auditoría)."""
    with transaction.atomic():
        target.first_name = first_name
        target.last_name = last_name
        target.save(update_fields=["first_name", "last_name"])
    return target


@audit(action="UPDATE", entity="User")
def reset_password(*, user: User, target: User, raw_password: str) -> User:
    """Fija la contraseña temporal, activa el flag de cambio forzado e invalida sesiones.

    La contraseña (dada por el admin o generada) ya viene resuelta. Devuelve el usuario
    afectado para que la auditoría lo atribuya; el actor va en `user`.
    """
    with transaction.atomic():
        target.set_password(raw_password)
        target.must_change_password = True
        target.save(update_fields=["password", "must_change_password"])
        revoke_all_refresh(target)
    return target


@audit(action="UPDATE", entity="User")
def deactivate_user(*, user: User, target: User) -> User:
    """Desactiva al usuario e invalida todos sus refresh. `user` es el actor (auditoría)."""
    with transaction.atomic():
        target.is_active = False
        target.save(update_fields=["is_active"])
        revoke_all_refresh(target)
    return target


@audit(action="UPDATE", entity="User")
def reactivate_user(*, user: User, target: User) -> User:
    """Reactiva al usuario. `user` es el actor (auditoría)."""
    with transaction.atomic():
        target.is_active = True
        target.save(update_fields=["is_active"])
    return target
