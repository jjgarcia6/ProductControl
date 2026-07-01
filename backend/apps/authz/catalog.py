"""Catálogo central de autorización (capability access-control, F2).

Fuente única de la ESTRUCTURA de permisos: qué módulos existen, qué acciones son
válidas por módulo y qué campos están registrados como sensibles. Cada fase posterior
AÑADE aquí su módulo, sus acciones y sus campos sensibles; los perfiles solo pueden
referenciar claves que existan en este catálogo (lo valida el serializer).

Es solo DATOS (sin imports de Django) para poder reutilizarse desde migraciones,
servicios y tests sin riesgo de import circular.
"""

from __future__ import annotations

from typing import TypedDict

# --- Módulos -----------------------------------------------------------------
MODULE_ACCESS_CONTROL = "access-control"
MODULE_DIRECTORY = "directory"  # F4: gestión del Directorio (fichas de tercero)
MODULE_PRODUCTS = "products"  # F5: maestro de inventario (categorías, productos, unidades)

# --- Acciones ----------------------------------------------------------------
ACTION_READ = "read"
ACTION_CREATE = "create"
ACTION_UPDATE = "update"
ACTION_DELETE = "delete"

# Catálogo de pares (módulo -> acciones permitidas). F2 registra el módulo de
# perfiles/identidad; las fases siguientes añaden los suyos.
PERMISSION_CATALOG: dict[str, frozenset[str]] = {
    MODULE_ACCESS_CONTROL: frozenset({ACTION_READ, ACTION_CREATE, ACTION_UPDATE}),
    MODULE_DIRECTORY: frozenset({ACTION_READ, ACTION_CREATE, ACTION_UPDATE}),
    MODULE_PRODUCTS: frozenset({ACTION_READ, ACTION_CREATE, ACTION_UPDATE}),
}

# Registro de campos sensibles, como claves "recurso.campo". F2 entrega el MECANISMO;
# el primer campo real (`intake.cost`) lo registra F12. Hasta entonces está vacío.
SENSITIVE_FIELDS: frozenset[str] = frozenset()


def is_valid_permission(module: str, action: str) -> bool:
    """¿El par (módulo, acción) existe en el catálogo conocido?"""
    return action in PERMISSION_CATALOG.get(module, frozenset())


# --- Perfiles semilla del sistema --------------------------------------------
class SystemProfileSpec(TypedDict):
    name: str
    permissions: dict[str, list[str]]
    auto_approval: bool


# Un perfil por rol del sistema. Las claves son los VALORES de accounts.Role
# (estables); el seed crea los perfiles y el backfill asigna a cada usuario el
# perfil cuyo rol coincide. Permisos por defecto coherentes con cada rol.
SYSTEM_PROFILES: dict[str, SystemProfileSpec] = {
    "JEFE": {
        "name": "Jefe",
        "permissions": {MODULE_ACCESS_CONTROL: [ACTION_READ, ACTION_CREATE, ACTION_UPDATE]},
        "auto_approval": True,
    },
    "SUPERVISOR": {
        "name": "Supervisor",
        "permissions": {MODULE_ACCESS_CONTROL: [ACTION_READ]},
        "auto_approval": False,
    },
    "RUTA": {
        "name": "Responsable de ruta",
        "permissions": {},
        "auto_approval": False,
    },
    "USUARIO": {
        "name": "Usuario",
        "permissions": {},
        "auto_approval": False,
    },
}

# Mapa inverso nombre-de-perfil-semilla -> valor de rol nominal (accounts.Role). F3 lo usa
# para sincronizar el `role` al asignar/crear con un perfil semilla. Los perfiles a medida
# (sin entrada aquí) no alteran el rol nominal.
PROFILE_NAME_TO_ROLE: dict[str, str] = {
    spec["name"]: role for role, spec in SYSTEM_PROFILES.items()
}


def role_for_profile_name(name: str) -> str | None:
    """Rol nominal que corresponde a un perfil semilla, o None si es a medida."""
    return PROFILE_NAME_TO_ROLE.get(name)
