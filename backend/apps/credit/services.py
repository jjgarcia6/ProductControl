"""Lógica de negocio de términos de crédito (capability credit, F4).

Términos por faceta (CLIENTE/PROVEEDOR) de una ficha. En F4 son **solo datos**. Las
reglas de integridad —faceta↔rol y unicidad por (ficha, faceta)— viven aquí y se
emiten por el contrato uniforme: `ValidationError` (400, en el campo `facet`) y
`Conflict` (409). Toda escritura va en `transaction.atomic()` y se audita.
"""

from __future__ import annotations

from typing import Any

from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.accounts.models import User
from apps.common.audit import audit
from apps.common.exceptions import Conflict
from apps.directory.models import Ficha, FichaRole

from .models import CreditFacet, CreditTerms

# Cada faceta exige que la ficha tenga el rol correspondiente.
_FACET_REQUIRED_ROLE: dict[str, str] = {
    CreditFacet.CLIENTE: FichaRole.CLIENTE,
    CreditFacet.PROVEEDOR: FichaRole.PROVEEDOR,
}


def _ensure_facet_matches_role(ficha: Ficha, facet: str) -> None:
    """La faceta CLIENTE/PROVEEDOR exige el rol homónimo en la ficha (400 si no)."""
    required_role = _FACET_REQUIRED_ROLE[facet]
    if required_role not in (ficha.roles or []):
        raise ValidationError(
            {"facet": [f"La ficha no tiene el rol requerido para la faceta {facet}."]}
        )


@audit(action="CREATE", entity="CreditTerms")
def create_terms(*, user: User, data: dict[str, Any]) -> CreditTerms:
    """Crea los términos de una faceta (409 si ya existen para esa (ficha, faceta))."""
    ficha: Ficha = data["ficha"]
    facet: str = data["facet"]
    _ensure_facet_matches_role(ficha, facet)
    with transaction.atomic():
        if CreditTerms.objects.filter(ficha=ficha, facet=facet).exists():
            raise Conflict("Ya existen términos de crédito para esta ficha y faceta.")
        terms = CreditTerms.objects.create(**data)
    return terms


@audit(action="UPDATE", entity="CreditTerms")
def update_terms(*, user: User, terms: CreditTerms, data: dict[str, Any]) -> CreditTerms:
    """Edita términos existentes; revalida faceta↔rol y unicidad si cambia la faceta."""
    new_facet = data.get("facet", terms.facet)
    with transaction.atomic():
        _ensure_facet_matches_role(terms.ficha, new_facet)
        if new_facet != terms.facet and (
            CreditTerms.objects.filter(ficha=terms.ficha, facet=new_facet)
            .exclude(pk=terms.pk)
            .exists()
        ):
            raise Conflict("Ya existen términos de crédito para esta ficha y faceta.")
        for field, value in data.items():
            setattr(terms, field, value)
        terms.save()
    return terms
