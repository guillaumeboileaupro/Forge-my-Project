"""Archive ZIP en memoire d'un ensemble de fichiers deja rendus."""
import io
import zipfile

from forge.generator.paths import safe_relative_path

# Horodatage fixe : deux generations identiques produisent la meme archive.
FIXED_DATE = (2026, 1, 1, 0, 0, 0)


def build_zip(root, files):
    """Chaque entree est placee sous `root/` ; tout chemin non sur est refuse."""
    safe_relative_path(root)
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(files):
            info = zipfile.ZipInfo("%s/%s" % (root, safe_relative_path(path)), FIXED_DATE)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, files[path])
    return stream.getvalue()
