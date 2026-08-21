---
name: Bug Report
about: Reportar un error o comportamiento inesperado
title: "[BUG] "
labels: bug
assignees: alej-developer
---

## Descripcion

<!-- Descripcion clara y concisa del problema. -->

## Pasos para Reproducir

1. Enviar peticion al endpoint `POST /api/v1/...` con el payload `{...}`
2. Observar la respuesta devuelta.
3. Comportamiento anomalo observado.

## Comportamiento Esperado

<!-- Descripcion de lo que se esperaba que sucediera. -->

## Comportamiento Actual

<!-- Codigo de estado HTTP y cuerpo de respuesta obtenido. -->

```json
{
  "exito": false,
  "error": "...",
  "detalles": {}
}
```

## Entorno

- **Sistema Operativo:** Windows / Linux / macOS
- **Python:** `python --version`
- **Commit:** `git log --oneline -1`
