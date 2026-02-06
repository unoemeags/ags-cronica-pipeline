# Sheet schema (Mesa de redaccion - AGS)

Encabezados recomendados (fila 1):

id
fecha_detectada
hora_detectada
fuente
titulo_original
link
tema_sugerido
actor_sugerido
resumen_neutral
relevancia
publicar
tipo_contenido
hora_recomendada
notas_editor
hash_dedupe

Notas:
- `publicar` se deja vacio. El editor marca si/no.
- `hash_dedupe` es un hash estable para evitar duplicados (por URL normalizada).
