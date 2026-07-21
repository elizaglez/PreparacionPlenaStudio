# Preparación Plena Studio

Entrega 1 funcional.

Incluye:
- Interfaz de escritorio con navegación lateral.
- Creación y apertura de proyectos.
- Selección y copia de PDF, MP3 y citas bíblicas.
- Historial local.
- Configuración.
- Metodología PPA persistente.

## Ejecutar en Windows

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

## Estructura de cada proyecto

```text
NombreDelProyecto/
├── fuente/
│   ├── articulo.pdf
│   ├── audio.mp3
│   └── citas.txt
├── trabajo/
├── exportaciones/
├── recursos/
└── proyecto.json
```
