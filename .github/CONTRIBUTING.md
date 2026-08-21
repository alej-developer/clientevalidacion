# Guía de Contribución

¡Gracias por tu interés en contribuir a **clientevalidacion**! 🎉
Sigue estas pautas para mantener la calidad y consistencia del proyecto.

---

## 🚀 Flujo de trabajo

1. **Fork** del repositorio y clona tu fork
2. Crea una rama descriptiva desde `main`:
   ```bash
   git checkout -b feat/nombre-de-la-funcionalidad
   # o
   git checkout -b fix/descripcion-del-bug
   ```
3. Haz tus cambios con commits atómicos y bien descritos
4. Asegúrate de que **todos los tests pasen** y añade nuevos si es necesario
5. Abre un **Pull Request** hacia `main` con una descripción clara

---

## 📝 Convención de Commits

Usamos **Conventional Commits**. Formato:

```
<tipo>(<alcance>): <descripción en minúsculas>
```

### Tipos permitidos

| Tipo | Cuándo usarlo |
|------|---------------|
| `feat` | Nueva funcionalidad |
| `fix` | Corrección de bug |
| `test` | Añadir o corregir tests |
| `docs` | Solo documentación |
| `refactor` | Refactorización sin cambio funcional |
| `ci` | Configuración de CI/CD |
| `chore` | Dependencias, herramientas, configuración |
| `perf` | Mejoras de rendimiento |

### Ejemplos válidos

```bash
feat(auth): implementar autenticacion JWT y proteccion de endpoints
fix(repositorio): corregir filtro de soft delete en listar_paginado
test(api): añadir casos de prueba para paginación
docs: actualizar README con guia de instalacion
refactor(servicio): extraer validacion de email a modulo compartido
chore(deps): actualizar fastapi a 0.116.0
```

---

## ✅ Estándares de calidad

Antes de hacer un PR, asegúrate de pasar todas las comprobaciones:

```bash
# 1. Tests (deben pasar al 100%)
pytest -v

# 2. Linting con Ruff
ruff check .

# 3. Tipos con mypy
mypy app

# 4. Formateo (Ruff también formatea)
ruff format .
```

---

## 🏗 Arquitectura del proyecto

El proyecto sigue una arquitectura limpia de 4 capas:

```
API (endpoints)  →  Servicios (negocio)  →  Repositorios (datos)  →  Modelos (ORM)
```

- **No saltes capas**: los endpoints no hablan con repositorios directamente.
- **Sin lógica de negocio en endpoints**: va siempre en `servicios/`.
- **Sin SQL crudo en servicios**: va siempre en `repositorios/`.

---

## 🧪 Tests

- Cada nueva funcionalidad debe incluir **al menos un test de integración**.
- Los tests usan SQLite en memoria, aislada por test (fixture `preparar_base_datos`).
- Los endpoints protegidos por JWT deben tener tests con y sin token.

---

## 🐛 Reportar bugs

Usa la [plantilla de bug report](.github/ISSUE_TEMPLATE/bug_report.md) en GitHub Issues.

---

## ❓ Preguntas

Abre un Issue con la etiqueta `question` si tienes dudas sobre el proyecto.
