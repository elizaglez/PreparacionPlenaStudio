import re, shutil
from datetime import datetime
from pathlib import Path
from app.models import Project, ProjectSources
from app.persistence import load_project as load_project_file
from app.persistence import remember_project, save_project

class ProjectError(RuntimeError):
    pass

def slugify(name):
    clean = re.sub(r'[<>:"/\\|?*]+', "-", name.strip())
    clean = re.sub(r"\s+", " ", clean).strip(" .")
    if not clean:
        raise ProjectError("El nombre del proyecto no puede estar vacío.")
    return clean

def copy_required(source, destination, label):
    src = Path(source)
    if not src.is_file():
        raise ProjectError(f"No se encontró el archivo de {label}.")
    shutil.copy2(src, destination)
    return str(destination.relative_to(destination.parents[1]))

def create_project(name, base_folder, pdf_path, audio_path, bible_path):
    safe_name = slugify(name)
    base = Path(base_folder).expanduser()
    base.mkdir(parents=True, exist_ok=True)
    root = base / safe_name
    if root.exists() and any(root.iterdir()):
        raise ProjectError("Ya existe una carpeta con ese nombre y no está vacía.")

    source = root / "fuente"
    work = root / "trabajo"
    exports = root / "exportaciones"
    resources = root / "recursos"
    for folder in (source, work, exports, resources):
        folder.mkdir(parents=True, exist_ok=True)

    try:
        pdf_rel = copy_required(pdf_path, source / "articulo.pdf", "PDF")
        audio_rel = copy_required(audio_path, source / "audio.mp3", "audio")
        bible_rel = copy_required(bible_path, source / "citas.txt", "citas bíblicas")
        now = datetime.now().astimezone().isoformat(timespec="seconds")
        project = Project(
            name=safe_name,
            created_at=now,
            updated_at=now,
            root=str(root.resolve()),
            sources=ProjectSources(pdf=pdf_rel, audio=audio_rel, bible=bible_rel),
        )
        save_project(project)
        remember_project(project)
        return project
    except Exception:
        shutil.rmtree(root, ignore_errors=True)
        raise

def load_project(path):
    p = Path(path)
    if p.is_dir():
        p = p / "proyecto.json"
    if not p.is_file():
        raise ProjectError("No se encontró proyecto.json.")
    try:
        project = load_project_file(p)
    except Exception as exc:
        raise ProjectError("El proyecto está dañado o no se puede leer.") from exc
    remember_project(project)
    return project
