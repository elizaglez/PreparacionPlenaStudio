# Preparación Plena Studio

## Entrega 5 — Motor de prompts y validación

Esta versión separa las instrucciones de IA del código y añade una capa formal
de control de calidad antes de guardar el MASTER.

### Funciones nuevas

- Prompts versionados en la carpeta `prompts/`.
- Cargador de plantillas con variables obligatorias.
- Prompt del sistema separado del prompt de cada pregunta.
- Validación automática de `master.json`.
- Comprobación de que todas las preguntas tengan respuesta.
- Verificación de que las preguntas se conserven literalmente.
- Detección de respuestas vacías, duplicadas o huérfanas.
- Advertencias cuando se pierden referencias bíblicas.
- Informe de calidad en `trabajo/master_validacion.json`.
- La regeneración de una respuesta también se valida antes de guardarse.

### Flujo actualizado

```text
articulo.json
      ↓
prompts/system.md + prompts/answer.md
      ↓
OpenAI
      ↓
MASTER provisional
      ↓
validación estructural
      ↓
master.json + master_validacion.json
```

### Archivos de prompts

```text
prompts/
├── system.md
└── answer.md
```

Los prompts pueden revisarse y versionarse en Git sin modificar el código Python.

### Ejecutar

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

### Pruebas

```bash
python -m unittest discover -s tests
```

La aplicación no guarda `master.json` cuando existen errores estructurales.
Las advertencias no bloquean el proceso, pero quedan registradas para revisión.
