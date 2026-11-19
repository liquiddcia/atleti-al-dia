# Vídeos de noticias

Cada vídeo es un archivo `videos/<nombre>.json`. Para generarlo:

- **A mano:** pestaña *Actions* → «Vídeo noticia» → *Run workflow* y escribe el nombre
  (sin `.json`, por ejemplo `cuti`).
- **Automático:** al subir o cambiar un `videos/*.json`, se generan los vídeos de los
  json que hayan cambiado.

El mp4 queda como artefacto `video-<nombre>` de la ejecución.

## Formato

```json
{
  "titular": ["PRIMERA LÍNEA", "SEGUNDA LÍNEA"],
  "frases": [
    {"hablado": "Suma veinticinco puntos.", "subtitulo": "Suma 25 puntos."}
  ],
  "imagen": { ... }
}
```

- `titular`: las líneas del titular rojo (normalmente 2). El tamaño se ajusta solo.
- `frases`: lo que dice la voz (`hablado`, con las cifras escritas con letras) y lo que
  sale en el subtítulo (`subtitulo`). Si solo pones uno, se usa para las dos cosas.
- `imagen`: el panel central, que hace el zoom lento. Dos tipos:

**Barras**

```json
{
  "tipo": "barras",
  "titulo": "MEJORES ARRANQUES EN LIGA · 10 JORNADAS",
  "maximo": 30,
  "formato": "{valor}/30",
  "barras": [{"etiqueta": "2026-27", "valor": 25, "destacada": true}],
  "pie": "Texto opcional en la franja roja"
}
```

**Lista** (filas con un punto de color: `verde`, `ambar`, `rojo` o `gris`)

```json
{
  "tipo": "lista",
  "titulo": "ENTRENAMIENTO · MARTES",
  "filas": [{"nombre": "Koke", "estado": "Toca balón y sprints", "color": "verde"}],
  "pie": "Sábado: Levante · Ciutat de Valencia"
}
```
