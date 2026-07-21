# Arquitectura de Preparación Plena Studio

## Flujo principal

```text
Fuentes (PDF / MP3 / Biblia)
        ↓
Procesamiento y parser
        ↓
articulo.json + citas_extraidas.txt
        ↓
ContextBuilder
        ↓
PipelineEngine
  ├─ respuesta principal
  ├─ explicación bíblica
  ├─ comparación
  ├─ aplicación
  └─ nota de imagen
        ↓
Validación
        ↓
master.json
        ↓
Editor / Historial / Exportación
```

## Motor de pipeline

El paquete `app/pipeline` separa la generación en etapas pequeñas, trazables y
regenerables. Cada etapa tiene estado propio (`pending`, `running`, `completed`,
`failed`, `skipped`) y sus resultados se guardan en
`trabajo/pipeline_estado.json`.

Las etapas pueden ejecutarse completas o de manera individual. Las etapas
secundarias dependen de la respuesta principal, lo que evita producir contenido
sin una base aprobable.

## Principio de diseño

La Biblia es la autoridad, la publicación es la guía y la IA funciona solamente
como editora. El pipeline no añade doctrina: organiza la producción editorial y
conserva trazabilidad sobre cada generación.
