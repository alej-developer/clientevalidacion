# Guia de Contribucion

Pautas para contribuir al proyecto manteniendo calidad, estilo y consistencia.

---

## Flujo de Trabajo

1. Realizar un Fork del repositorio y clonar la rama de trabajo.
2. Crear una rama descriptiva desde `main`:
   ```bash
   git checkout -b feat/nombre-de-la-funcionalidad
   # o
   git checkout -b fix/descripcion-del-bug
   ```
3. Realizar los cambios con commits atomicos y bien documentados.
4. Asegurar que todos los tests pasen y agregar pruebas para la nueva funcionalidad.
5. Abrir un Pull Request hacia la rama `main` con descripcion detallada.

---

## Convencion de Commits

El proyecto sigue la especificacion de Conventional Commits:

```
<tipo>(<alcance>): <descripcion en minusculas>
```

### Tipos Permitidos

| Tipo | Descripcion |
|------|-------------|
| `feat` | Nueva funcionalidad |
| `fix` | Correccion de errores |
| `test` | Incorporacion o correccion de pruebas |
| `docs` | Modificaciones exclusivas en documentacion |
| `refactor` | Refactorizacion de codigo sin alteracion funcional |
| `ci` | Configuracion de integracion continua y despliegue |
| `chore` | Actualizacion de dependencias o configuraciones menores |
| `perf` | Optimizaciones de rendimiento |

### Ejemplos

```bash
feat(auth): implementar autenticacion JWT y proteccion de endpoints
fix(repositorio): corregir filtro de soft delete en listar_paginado
test(api): anadir casos de prueba para busqueda y ordenacion
docs: actualizar documentacion de instalacion y configuracion
```

---

## Estandares de Calidad

Antes de enviar un Pull Request, ejecutar las siguientes validaciones:

```bash
# 1. Pruebas unitarias e integracion
pytest -v

# 2. Analisis estatico de codigo con Ruff
ruff check .

# 3. Verificacion de formato
ruff format . --check

# 4. Comprobacion de tipos estaticos con mypy
mypy app
```

---

## Arquitectura

El diseno sigue una arquitectura en capas bien diferenciadas:

```
API (endpoints) -> Servicios (negocio) -> Repositorios (datos) -> Modelos (ORM)
```

- Cada capa solo se comunica con su nivel inmediatamente inferior.
- La logica de negocio reside exclusivamente en `app/servicios/`.
- El acceso a base de datos se canaliza a traves de `app/repositorios/`.
