# Prompt Library

Biblioteca organizada de prompts reutilizables extraídos de sesiones de Copilot CLI.

## Estructura

```
prompts/
├── refactoring/     # Prompts para refactorización de código
├── testing/         # Prompts para testing y QA
├── debugging/       # Prompts para debugging y fixes
├── implementation/  # Prompts para nuevas features
├── code-review/     # Prompts para revisión de código
├── documentation/   # Prompts para documentación
├── general/         # Otros prompts
├── index.json      # Índice searchable
└── README.md       # Este archivo
```

## Uso Rápido

1. **Buscar por categoría**: Navega a la carpeta correspondiente
2. **Buscar por keyword**: Consulta `index.json` sección `tags`
3. **Ver todas las sesiones**: Revisa `index.json` sección `sessions`

## Cómo Usar un Template

Cada prompt incluye:
- Metadata (tipo, fecha, keywords)
- Secciones estructuradas (si están disponibles)
- Prompt original
- Variables de template para personalizar

Ejemplo:
```markdown
{{PROJECT_NAME}} = "MiProyecto"
{{CONTEXT}} = "Backend en Node.js con Express"
{{SPECIFIC_TASK}} = "Optimizar queries de base de datos"
```

## Añadir Nuevas Sesiones

```bash
python prompt_organizer.py --organize *.md
```

## Comandos Útiles

```bash
# Organizar todas las sesiones
python prompt_organizer.py --organize copilot-session-*.md

# Buscar por keyword
grep -r "refactor" prompts/

# Ver índice
cat prompts/index.json | jq .
```
