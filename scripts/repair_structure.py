from pathlib import Path
import re
import shutil

ROOT = Path(".")
APP_MAIN = ROOT / "app" / "src" / "main"
JAVA_ROOT = APP_MAIN / "java"
RES_ROOT = APP_MAIN / "res"

PACKAGE_RE = re.compile(r"^\s*package\s+([a-zA-Z0-9_.]+)", re.MULTILINE)

def ensure_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)

def move_file(src: Path, dst: Path):
    if src.resolve() == dst.resolve():
        return
    ensure_dir(dst.parent)
    if dst.exists():
        if dst.read_text(encoding="utf-8", errors="ignore") == src.read_text(encoding="utf-8", errors="ignore"):
            src.unlink()
            return
        backup = dst.with_suffix(dst.suffix + ".backup")
        shutil.move(str(dst), str(backup))
    shutil.move(str(src), str(dst))
    print(f"MOVED: {src} -> {dst}")

def classify_xml(path: Path) -> Path:
    name = path.name

    values = {
        "strings.xml",
        "themes.xml",
        "colors.xml",
        "styles.xml",
    }

    xml = {
        "backup_rules.xml",
        "data_extraction_rules.xml",
        "widget_small_info.xml",
        "widget_medium_info.xml",
        "widget_large_info.xml",
    }

    layout = {
        "widget_small.xml",
        "widget_medium.xml",
        "widget_large.xml",
    }

    if name in values:
        return RES_ROOT / "values" / name
    if name in xml:
        return RES_ROOT / "xml" / name
    if name in layout:
        return RES_ROOT / "layout" / name

    if name.startswith("ic_") or "background" in name:
        return RES_ROOT / "drawable" / name

    return RES_ROOT / "xml" / name

def repair_kotlin_files():
    for path in list(APP_MAIN.rglob("*.kt")):
        text = path.read_text(encoding="utf-8", errors="ignore")
        match = PACKAGE_RE.search(text)
        if not match:
            continue

        package = match.group(1)
        package_path = Path(*package.split("."))
        dst = JAVA_ROOT / package_path / path.name
        move_file(path, dst)

def repair_xml_files():
    for path in list(APP_MAIN.rglob("*.xml")):
        if path.name == "AndroidManifest.xml":
            continue

        if "build" in path.parts:
            continue

        dst = classify_xml(path)
        move_file(path, dst)

def remove_wrong_files():
    patterns = [
        "setup_project.py",
        "fix_errors.py",
        "fix_final.py",
        "fix_final_v2.py",
        "fix_canvas_final.py",
        "fix_structure.py",
        "scripts/create_resources.py",
        "app/src/main/res/xml/create_resources.py",
    ]

    for pattern in patterns:
        path = ROOT / pattern
        if path.exists():
            if path.is_file():
                path.unlink()
                print(f"DELETED: {path}")
            elif path.is_dir():
                shutil.rmtree(path)
                print(f"DELETED DIR: {path}")

    for path in list(JAVA_ROOT.rglob("*")):
        if path.is_file() and path.suffix in {".md", ".yml", ".yaml", ".py"}:
            path.unlink()
            print(f"DELETED MISPLACED: {path}")

def remove_empty_dirs():
    for path in sorted(APP_MAIN.rglob("*"), reverse=True):
        if path.is_dir():
            try:
                path.rmdir()
            except OSError:
                pass

def main():
    ensure_dir(JAVA_ROOT)
    ensure_dir(RES_ROOT / "values")
    ensure_dir(RES_ROOT / "xml")
    ensure_dir(RES_ROOT / "drawable")
    ensure_dir(RES_ROOT / "layout")

    repair_kotlin_files()
    repair_xml_files()
    remove_wrong_files()
    remove_empty_dirs()

    print("Project structure repair completed.")

if __name__ == "__main__":
    main()