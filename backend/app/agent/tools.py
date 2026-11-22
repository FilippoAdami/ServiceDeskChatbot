from __future__ import annotations

from google.genai import types

CREATE_TICKET_TOOL = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="create_ticket",
            description=(
                "Apre un ticket di supporto IT nel Service Desk aziendale per richiedere l'intervento o la presa "
                "in carico da parte di un tecnico umano specializzato quando l'utente richiede assistenza, oppure "
                "quando le procedure della Knowledge Base sono assenti o insufficienti a risolvere il problema."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "title": types.Schema(
                        type=types.Type.STRING,
                        description=(
                            "Titolo sintetico ed esplicativo del problema IT "
                            "(es. 'Blocco casuale schermo PC e riavvii forzati')"
                        ),
                    ),
                    "symptoms": types.Schema(
                        type=types.Type.STRING,
                        description=(
                            "Descrizione dettagliata dei sintomi e del comportamento anomalo "
                            "osservato dall'utente"
                        ),
                    ),
                    "reason": types.Schema(
                        type=types.Type.STRING,
                        description=(
                            "Motivazione dell'escalation "
                            "(es. 'Richiesta esplicita' oppure 'Procedura non presente in Knowledge Base')"
                        ),
                    ),
                    "priority": types.Schema(
                        type=types.Type.STRING,
                        description="Priorità stimata per il ticket: 'low', 'medium', 'high', o 'critical'",
                    ),
                },
                required=["title", "symptoms", "reason"],
            ),
        )
    ]
)
