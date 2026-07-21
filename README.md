# Preparación Plena Studio

## Entrega 6 — Editor inteligente del MASTER

Esta versión convierte el generador en un flujo de revisión pregunta por
pregunta.

### Funciones nuevas

- Editor visual de cada respuesta.
- Edición independiente de respuesta, explicación bíblica, comparación,
  aplicación y nota de imagen.
- Estados: pendiente, revisada, aprobada, regenerada y editada.
- Regeneración de una sola respuesta.
- Guardado en `trabajo/master.json`.
- Contador general de respuestas revisadas y aprobadas.
- Compatibilidad con MASTER anteriores sin campo `status`.

### Flujo

```text
master.json
    ↓
Editor del MASTER
    ↓
Editar / regenerar / aprobar
    ↓
master.json actualizado
    ↓
Exportación
```

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
