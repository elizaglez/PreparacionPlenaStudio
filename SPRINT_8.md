# Sprint 8 — Motor de pipeline

## Implementado

- Motor de etapas reutilizable en `app/pipeline/`.
- Estados persistentes por pregunta y etapa.
- Generación separada de respuesta, explicación bíblica, comparación,
  aplicación y nota de imagen.
- Regeneración individual de etapas desde el editor.
- Registro de cada solicitud con el nombre de su etapa.
- Documento de arquitectura.
- Pruebas automatizadas del pipeline.

## Verificación local

```text
python -m unittest discover -s tests -v
21 pruebas ejecutadas correctamente.
python -m compileall -q app tests
Sin errores de sintaxis.
```
