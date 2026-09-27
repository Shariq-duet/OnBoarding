import ast
import json
import sys
from pathlib import Path
from typing import Dict, List, Any

class RepositoryASTVisitor(ast.NodeVisitor):
    def __init__(self, file_path: Path, root_path: Path):
        self.file_path = file_path
        self.rel_path = str(file_path.relative_to(root_path)).replace("\\", "/")
        self.imports: List[str] = []
        self.classes: List[Dict[str, Any]] = []
        self.functions: List[Dict[str, Any]] = []
        self.has_main_block = False
        self.detected_frameworks: List[str] = []

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            self.imports.append(alias.name)
            self._check_framework(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.module:
            self.imports.append(node.module)
            self._check_framework(node.module)
        self.generic_visit(node)

    def _check_framework(self, name: str):
        frameworks = ["fastapi", "flask", "cv2", "ultralytics", "torch", "sqlalchemy", "click", "argparse", "celery"]
        for fw in frameworks:
            if fw in name.lower() and fw not in self.detected_frameworks:
                self.detected_frameworks.append(fw)

    def visit_ClassDef(self, node: ast.ClassDef):
        bases = [b.id for b in node.bases if isinstance(b, ast.Name)]
        methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
        self.classes.append({
            "name": node.name,
            "line": node.lineno,
            "bases": bases,
            "methods": methods,
            "docstring": ast.get_docstring(node) or ""
        })
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        args = [arg.arg for arg in node.args.args]
        self.functions.append({
            "name": node.name,
            "line": node.lineno,
            "arguments": args,
            "docstring": ast.get_docstring(node) or ""
        })
        self.generic_visit(node)

    def visit_If(self, node: ast.If):
        # Look for: if __name__ == '__main__':
        if isinstance(node.test, ast.Compare):
            left = node.test.left
            if isinstance(left, ast.Name) and left.id == "__name__":
                for comp in node.test.comparators:
                    if isinstance(comp, ast.Constant) and comp.value == "__main__":
                        self.has_main_block = True
        self.generic_visit(node)


def scan_repository(target_dir: str = ".") -> Dict[str, Any]:
    root = Path(target_dir).resolve()
    if not root.exists():
        raise FileNotFoundError(f"Target path does not exist: {target_dir}")

    ignore_dirs = {".git", ".bob", "venv", "env", "__pycache__", ".pytest_cache", "node_modules", "dist", "build"}
    
    file_inventory = []
    all_frameworks = set()
    entry_candidates = []
    total_loc = 0

    python_files = [p for p in root.rglob("*.py") if not any(part in ignore_dirs for part in p.parts)]

    for py_file in python_files:
        try:
            content = py_file.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        loc = len(content.splitlines())
        total_loc += loc

        try:
            tree = ast.parse(content, filename=str(py_file))
            visitor = RepositoryASTVisitor(py_file, root)
            visitor.visit(tree)

            all_frameworks.update(visitor.detected_frameworks)

            if visitor.has_main_block or "main.py" in py_file.name or "app.py" in py_file.name:
                entry_candidates.append(visitor.rel_path)

            file_inventory.append({
                "path": visitor.rel_path,
                "lines_of_code": loc,
                "imports": visitor.imports,
                "classes": visitor.classes,
                "functions": visitor.functions,
                "has_entry_hook": visitor.has_main_block
            })
        except SyntaxError:
            file_inventory.append({
                "path": str(py_file.relative_to(root)).replace("\\", "/"),
                "lines_of_code": loc,
                "error": "SyntaxError during AST parse"
            })

    # Read configuration and documentation manifests if present
    readme_sample = ""
    for r_name in ["README.md", "readme.md", "README.txt"]:
        r_path = root / r_name
        if r_path.exists():
            readme_sample = r_path.read_text(encoding="utf-8", errors="ignore")[:3000]
            break

    requirements = []
    req_file = root / "requirements.txt"
    if req_file.exists():
        requirements = [line.strip() for line in req_file.read_text(encoding="utf-8", errors="ignore").splitlines() if line.strip() and not line.startswith("#")]

    ast_package = {
        "root_directory": str(root),
        "total_python_files": len(python_files),
        "total_lines_of_code": total_loc,
        "detected_frameworks": list(all_frameworks),
        "entry_candidates": entry_candidates,
        "requirements_declared": requirements[:20],
        "readme_preview": readme_sample,
        "files": file_inventory
    }

    output_path = Path("ast_inventory.json")
    output_path.write_text(json.dumps(ast_package, indent=2), encoding="utf-8")
    return ast_package


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "."
    print(f"[*] Scanning codebase at: {target}")
    result = scan_repository(target)
    print(f"[+] Found {result['total_python_files']} Python files ({result['total_lines_of_code']} LOC).")
    print(f"[+] Potential entry points: {result['entry_candidates']}")
    print(f"[+] Detected frameworks: {result['detected_frameworks']}")
    print(f"[+] Generated: ast_inventory.json")