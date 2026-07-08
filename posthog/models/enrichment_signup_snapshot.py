from django.db import models

from posthog.models.utils import UUIDModel


class EnrichmentSignupSnapshot(UUIDModel):
    """Write-once marker that the at-signup enrichment snapshot has been emitted for an org.

    Stores no firmographic values (those live only on the person-scoped snapshot event); this
    row is purely the idempotency guard and provenance timestamp. Kept in its own table rather
    than as a column on the hot organization table, and organization_id has no foreign key so
    the marker never takes a lock on that table.
    """

    organization_id = models.UUIDField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
