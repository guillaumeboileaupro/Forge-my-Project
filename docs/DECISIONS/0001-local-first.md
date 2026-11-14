# ADR-0001 - Generation locale sans dependances

Statut: accepte.

Contexte: les projets generes peuvent comprendre des choix sensibles et des secrets futurs.

Decision: le prototype fonctionne sur 127.0.0.1, avec la bibliotheque standard Python, sans reseau externe et sans execution de scripts generes.

Consequences: usage immediat et empreinte reduite, mais aucune verification live de packages ou d'API possible pour le moment. La verification devra etre une etape distincte, explicite et auditable.
