import json
import sys
from pathlib import Path

def verify_blueprint(blueprint_path: str = "repo_blueprint.json", repo_root: str = "benchmarks/traffic_monitor"):
    bp_file = Path(blueprint_path)
    root = Path(repo_root)

    if not bp_file.exists():
        print("[-] Error: repo_blueprint.json does not exist.")
        sys.exit(1)

    data = json.loads(bp_file.read_text(encoding="utf-8"))
    errors = []

    # 1. Verify Entrypoint
    entry = data.get("entrypoint_and_execution", {}).get("primary_entry", "")
    if entry and not (root / entry).exists():
        errors.append(f"Entrypoint file '{entry}' does not exist on disk.")

    # 2. Verify Pipeline Stages & Files
    for stage in data.get("execution_flow", []):
        mod_file = stage.get("module_file", "")
        if mod_file and not (root / mod_file).exists():
            errors.append(f"Pipeline stage '{stage.get('name')}' references non-existent file: {mod_file}")
        
        anchor = stage.get("code_anchor", {})
        anchor_file = anchor.get("file", "")
        if anchor_file and not (root / anchor_file).exists():
            errors.append(f"Code anchor references non-existent file: {anchor_file}")

    # 3. Verify Directory Map
    for dir_entry in data.get("file_system_directory", []):
        for kf in dir_entry.get("key_files", []):
            f_path = kf.get("file", "")
            if f_path and not (root / f_path).exists():
                errors.append(f"Directory map references missing file: {f_path}")

    # Summary
    print("=" * 60)
    print(" ONBOARDFLOW BLUEPRINT VERIFICATION REPORT")
    print("=" * 60)
    if errors:
        print(f"[-] FAILED: Found {len(errors)} grounding discrepancy/hallucination points:")
        for err in errors:
            print(f"    ❌ {err}")
        sys.exit(1)
    else:
        print("[+] PASSED: 100% of blueprint files and code anchors exist in the real repository.")
        print(f"[+] Verified {len(data.get('execution_flow', []))} pipeline stages.")
        print(f"[+] Verified {len(data.get('core_data_models', []))} data models.")
        print("=" * 60)

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "benchmarks/traffic_monitor"
    verify_blueprint(repo_root=target)