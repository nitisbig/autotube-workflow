import json
import subprocess
EXTENSIONS = {".png", ".jpeg", ".jpg", ".webp"}

def probe(path):
    return json.loads(subprocess.check_output([
        'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
        '-of', 'json', str(path)], text=True))['format']

def resolve_image(base, name):
    path = base / name
    if path.suffix.lower() in EXTENSIONS and path.is_file():
        return path
    directory = path.parent
    matches = sorted(p for p in directory.iterdir()
                     if p.stem == path.stem and p.suffix.lower() in EXTENSIONS) if directory.is_dir() else []
    if len(matches) != 1:
        raise ValueError(f'Expected one image for {name}; found {len(matches)}. Use an explicit filename to disambiguate.')
    return matches[0]
