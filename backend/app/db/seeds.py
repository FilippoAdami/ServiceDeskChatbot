from __future__ import annotations

import logging
from typing import List

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.db.models import Incident, IncidentStatus, utc_now

logger = logging.getLogger(__name__)

DEMO_INCIDENTS = [
    {
        "id": "INC-2026-001",
        "service": "Email",
        "title": "Degrado sincronizzazione e ritardi consegna Exchange / Outlook",
        "symptoms": (
            "Ritardo nella ricezione delle email (10-25 minuti), errori di sincronizzazione "
            "su client desktop Outlook e Webmail aziendale."
        ),
        "summary": (
            "Il cluster di posta elettronica aziendale sta registrando un incremento anomalo della coda "
            "di smistamento. Il team infrastruttura ha applicato una mitigazione e sta monitorando la "
            "stabilità del servizio."
        ),
        "status": IncidentStatus.MONITORING.value,
    },
    {
        "id": "INC-2026-002",
        "service": "VPN",
        "title": "Timeout autenticazione e disconnessioni gateway Cisco SecureConnect",
        "symptoms": (
            "Gli utenti da remoto riscontrano errore 'Authentication timeout' o frequenti disconnessioni "
            "ogni 15 minuti."
        ),
        "summary": (
            "Indagine in corso sui server RADIUS/MFA per timeout durante la fase di handshake VPN. "
            "Procedere con verifiche del certificato aziendale e autenticazione secondaria."
        ),
        "status": IncidentStatus.INVESTIGATING.value,
    },
    {
        "id": "INC-2026-003",
        "service": "Rete / Wi-Fi",
        "title": "Manutenzione programmata switch di piano Palazzina B",
        "symptoms": (
            "Interruzione temporanea connettività cablata e rete Wi-Fi aziendale nei piani 2 e 3 della Palazzina B."
        ),
        "summary": (
            "Aggiornamento firmware degli switch di dorsale completato con successo. Tutti i nodi sono "
            "rientrati nei parametri operativi."
        ),
        "status": IncidentStatus.RESOLVED.value,
    },
]


def seed_demo_incidents(db: Session) -> List[Incident]:
    """Seed demo incidents idempotently into the database."""
    seeded: List[Incident] = []
    now = utc_now()
    for inc_data in DEMO_INCIDENTS:
        existing = db.scalar(select(Incident).where(Incident.id == inc_data["id"]))
        if not existing:
            incident = Incident(
                id=inc_data["id"],
                service=inc_data["service"],
                title=inc_data["title"],
                symptoms=inc_data["symptoms"],
                summary=inc_data["summary"],
                status=inc_data["status"],
                created_at=now,
                updated_at=now,
            )
            db.add(incident)
            seeded.append(incident)
            logger.info("Seeded demo incident %s (%s)", incident.id, incident.title)
        else:
            seeded.append(existing)

    if seeded:
        db.commit()
    return seeded
