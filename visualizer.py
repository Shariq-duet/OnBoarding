"""
OnboardFlow — static HTML generator  (v3)
=========================================
Usage:
    python visualizer.py [blueprint.json]

    blueprint.json  path to a repo_blueprint JSON file
                    (default: fixtures/callbridge.json)

Tokens wired so far
-------------------
  Scalar (HTML-escaped):
    {{PROJECT_NAME}}, {{PROJECT_SLUG}}, {{PROJECT_VERSION}}, {{PROJECT_ARCHETYPE}}
    {{PROJECT_SUMMARY}}
    {{PRIMARY_PURPOSE}}, {{ARCHITECTURE_AND_CONTROL_FLOW}}, {{EDGE_CASES}}
    {{HW_GPU}}, {{HW_RAM}}, {{HW_NOTES}}
    {{ENTRY_FILE}}, {{EXECUTION_TYPE}}, {{RUN_COMMAND}}, {{LIFECYCLE_SUMMARY}}

  Block (pre-rendered HTML, injected raw):
    {{TECH_STACK_BADGES}}
    {{MERMAID_GRAPH}}        — raw Mermaid syntax; intentionally NOT html-escaped
    {{FLOW_CARDS}}           — one card per execution_flow stage (v2)
    {{DATA_MODEL_CARDS}}     — one card per core_data_models entry (v3)
    {{DIRECTORY_TABLE_ROWS}} — <tr> rows for file_system_directory (v3)
    {{SETUP_PREREQS}}        — <li> items for prerequisites (v3)
    {{SETUP_COMMANDS}}       — numbered copyable command blocks (v3)

All tokens are now wired. No remaining placeholders.

No third-party libraries required — stdlib only.
"""

import html
import json
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def e(value) -> str:
    """HTML-escape any value; returns '' for None."""
    if value is None:
        return ""
    return html.escape(str(value))


# ---------------------------------------------------------------------------
# Token builders
# ---------------------------------------------------------------------------

def build_flow_cards(flow: list) -> str:
    """
    Render execution_flow as horizontal-scroll stage cards matching OverFlow style.

    Each card renders:
      - step badge + module → symbol() header line
      - bold stage name
      - mechanism prose
      - IN / OUT contract blocks (coloured labels)
      - </> Anchor: file:lines header + syntax-highlighted snippet
    """
    cards = []
    for step in (flow or []):
        stage_id    = e(step.get("stage_id", ""))
        step_num    = e(step.get("step_number", ""))
        name        = e(step.get("name", ""))
        module_file = e(step.get("module_file", ""))
        mechanism   = e(step.get("mechanism", ""))
        symbol      = e(step.get("symbol_invoked", ""))
        input_c     = e(step.get("input_contract", ""))
        output_c    = e(step.get("output_contract", ""))

        anchor  = step.get("code_anchor") or {}
        file_   = e(anchor.get("file", ""))
        lines   = e(anchor.get("lines", ""))
        snippet = anchor.get("snippet", "")

        # ── IN / OUT contract blocks ──────────────────────────────────────────
        contracts_html = ""
        if input_c or output_c:
            in_block  = (
                f'<div class="contract-block">'
                f'<span class="contract-label contract-in">IN:</span>'
                f'<span class="contract-text">{input_c}</span>'
                f'</div>'
            ) if input_c else ""
            out_block = (
                f'<div class="contract-block">'
                f'<span class="contract-label contract-out">OUT:</span>'
                f'<span class="contract-text">{output_c}</span>'
                f'</div>'
            ) if output_c else ""
            contracts_html = f'<div class="contracts-wrap">{in_block}{out_block}</div>'

        # ── Code anchor block ─────────────────────────────────────────────────
        if snippet:
            caption = f"{file_}:{lines}" if file_ and lines else (file_ or "")
            anchor_block = (
                f'<div class="anchor-wrap">'
                # header bar: </> icon + file:lines + PYTHON label
                f'<div class="anchor-header">'
                f'<span class="anchor-icon">&lt;/&gt;</span>'
                f'<span class="anchor-caption">Anchor: {caption}</span>'
                f'<span class="anchor-lang">PYTHON</span>'
                f'</div>'
                f'<pre class="anchor-pre"><code class="language-python">{e(snippet)}</code></pre>'
                f'</div>'
            )
        else:
            anchor_block = ""

        # ── Assemble card ─────────────────────────────────────────────────────
        cards.append(
            f'<div id="stage-{stage_id}" class="flow-card">'

            # top accent bar
            f'<div class="flow-card-accent"></div>'

            f'<div class="flow-card-body">'

            # header row: Step N badge | module → symbol
            f'<div class="flow-card-header">'
            f'<span class="step-badge">Step {step_num}</span>'
            f'<span class="flow-card-sig">'
            f'<span class="sig-module">{module_file}</span>'
            + (f' <span class="sig-arrow">→</span> <span class="sig-symbol">{symbol}</span>' if symbol else "")
            + f'</span>'
            f'</div>'

            # stage name
            f'<h3 class="flow-card-name">{name}</h3>'

            # mechanism
            f'<p class="flow-card-mech">{mechanism}</p>'

            # IN / OUT contracts
            + contracts_html

            # code anchor
            + anchor_block

            + f'</div>'  # .flow-card-body
            + f'</div>'  # .flow-card
        )

    return "\n".join(cards)


def build_data_model_cards(models: list) -> str:
    """
    Render core_data_models as cards.
    Each card: entity_name header, defined_in label, field table (name / type / description).
    """
    cards = []
    for m in (models or []):
        entity   = e(m.get("entity_name", ""))
        defined  = e(m.get("defined_in", ""))

        field_rows = []
        for f in m.get("fields", []):
            field_rows.append(
                f'<tr class="hover:bg-subtle/20 transition-colors">'
                f'<td class="px-4 py-2.5 font-mono text-xs text-accent align-top">{e(f.get("name",""))}</td>'
                f'<td class="px-4 py-2.5 font-mono text-xs text-amber align-top whitespace-nowrap">{e(f.get("type",""))}</td>'
                f'<td class="px-4 py-2.5 text-xs text-faint">{e(f.get("description",""))}</td>'
                f'</tr>'
            )

        cards.append(
            f'<div class="bg-card border border-border rounded-xl overflow-hidden">'

            # header
            f'<div class="flex items-center justify-between px-4 py-3'
            f' border-b border-border bg-subtle/30">'
            f'  <span class="font-bold text-sm text-ink">{entity}</span>'
            f'  <span class="text-xs font-mono text-violet-400">{defined}</span>'
            f'</div>'

            # field table
            f'<div class="overflow-x-auto">'
            f'<table class="w-full text-sm">'
            f'<thead>'
            f'<tr class="border-b border-border">'
            f'<th class="px-4 py-2 text-left text-xs font-semibold uppercase tracking-wider text-muted">Field</th>'
            f'<th class="px-4 py-2 text-left text-xs font-semibold uppercase tracking-wider text-muted">Type</th>'
            f'<th class="px-4 py-2 text-left text-xs font-semibold uppercase tracking-wider text-muted">Description</th>'
            f'</tr>'
            f'</thead>'
            f'<tbody class="divide-y divide-border">'
            + "".join(field_rows)
            + f'</tbody></table></div>'
            f'</div>'
        )

    return "\n".join(cards)


def build_directory_table_rows(fsd: list) -> str:
    """
    Render file_system_directory as flat <tr> rows.
    Groups are separated by a muted directory+purpose header row.
    The table shell (<table>, <thead>) lives in template.html.
    """
    rows = []
    for d in (fsd or []):
        directory = e(d.get("directory", ""))
        purpose   = e(d.get("purpose", ""))

        # Directory header row spanning all columns
        rows.append(
            f'<tr class="bg-subtle/40">'
            f'<td colspan="3" class="px-5 py-2">'
            f'  <span class="font-mono text-xs font-bold text-ink">{directory}</span>'
            f'  <span class="ml-3 text-xs text-muted">{purpose}</span>'
            f'</td>'
            f'</tr>'
        )

        for f in d.get("key_files", []):
            rows.append(
                f'<tr class="hover:bg-subtle/20 transition-colors">'
                f'<td class="px-5 py-3 pl-8 font-mono text-xs text-accent">{e(f.get("file",""))}</td>'
                f'<td class="px-5 py-3 text-sm text-faint">{e(f.get("role",""))}</td>'
                f'<td class="px-5 py-3 text-xs text-muted text-right font-mono tabular-nums">{e(f.get("loc",""))}</td>'
                f'</tr>'
            )

    return "\n".join(rows)


def build_setup_prereqs(playbook: dict) -> str:
    """Render prerequisites as <li> items. The <ul> shell lives in template.html."""
    return "".join(
        f'<li class="flex items-start gap-2">'
        f'<span class="text-teal shrink-0 mt-0.5">›</span>'
        f'<span>{e(p)}</span>'
        f'</li>'
        for p in playbook.get("prerequisites", [])
    )


def build_setup_commands(playbook: dict) -> str:
    """
    Render each setup command as a copyable block.
    One Copy button per command — simpler than "copy all" and avoids
    needing to concatenate multi-line commands in JS.
    """
    blocks = []
    for c in playbook.get("commands", []):
        step_num = e(c.get("step", ""))
        title    = e(c.get("title", ""))
        command  = e(c.get("command", ""))

        blocks.append(
            f'<div class="cmd-block bg-card border border-border rounded-xl overflow-hidden">'

            # header bar: step pill + title + Copy button
            f'<div class="flex items-center justify-between px-5 py-3 border-b border-border">'
            f'  <div class="flex items-center gap-3">'
            f'    <span class="text-xs font-bold px-2 py-0.5 rounded-full'
            f'      bg-subtle text-muted border border-border">Step {step_num}</span>'
            f'    <span class="font-semibold text-sm text-ink">{title}</span>'
            f'  </div>'
            f'  <button class="copy-btn text-xs font-semibold px-3 py-1 rounded'
            f'    bg-subtle text-faint border border-border'
            f'    hover:text-ink transition-colors cursor-pointer">Copy</button>'
            f'</div>'

            # command body — plain <code> so hljs doesn't recolour shell syntax oddly
            f'<pre class="px-5 py-4 overflow-x-auto text-xs font-mono text-faint bg-[#0d1117]">'
            f'<code>{command}</code>'
            f'</pre>'

            f'</div>'
        )

    return "\n".join(blocks)


def build_tech_stack_badges(meta: dict) -> str:
    """Render tech_stack list as inline badge spans."""
    parts = []
    for t in meta.get("tech_stack", []):
        name    = e(t.get("name", ""))
        version = e(t.get("version", ""))
        parts.append(
            f'<span class="inline-block text-xs font-semibold font-mono px-2.5 py-1 rounded-md'
            f' bg-subtle text-faint border border-border">'
            f'{name} <span class="text-muted">{version}</span>'
            f'</span>'
        )
    return "\n".join(parts)


def build_tokens(blueprint: dict) -> dict:
    """
    Return a mapping of token → replacement value.

    Scalar values are HTML-escaped strings.
    Block values are pre-rendered HTML fragments (not escaped again).

    Only the tokens wired in v1 are populated; all others are intentionally
    absent so str.replace() leaves them untouched in the template.
    """
    meta  = blueprint.get("project_metadata", {})
    desc  = meta.get("project_description", {})
    hw    = meta.get("hardware_requirements", {})
    entry = blueprint.get("entrypoint_and_execution", {})

    return {
        # ── Scalar tokens ──────────────────────────────────────────────────
        "{{PROJECT_NAME}}":     e(meta.get("name")),
        "{{PROJECT_SLUG}}":     e(meta.get("slug")),
        "{{PROJECT_VERSION}}":  e(meta.get("version")),
        "{{PROJECT_ARCHETYPE}}": e(meta.get("archetype")),
        "{{PROJECT_SUMMARY}}":  e(meta.get("summary")),

        "{{PRIMARY_PURPOSE}}":               e(desc.get("primary_purpose")),
        "{{ARCHITECTURE_AND_CONTROL_FLOW}}":  e(desc.get("architecture_and_control_flow")),
        "{{EDGE_CASES}}":                    e(desc.get("edge_cases_and_invariants")),

        "{{HW_GPU}}":   "GPU recommended" if hw.get("gpu_recommended") else "CPU only",
        "{{HW_RAM}}":   e(hw.get("min_ram_gb", "?")),
        "{{HW_NOTES}}": e(hw.get("notes")),

        "{{ENTRY_FILE}}":        e(entry.get("primary_entry")),
        "{{EXECUTION_TYPE}}":    e(entry.get("execution_type")),
        "{{RUN_COMMAND}}":       e(entry.get("sample_run_command")),
        "{{LIFECYCLE_SUMMARY}}": e(entry.get("lifecycle_summary")),

        # ── Block tokens ───────────────────────────────────────────────────
        "{{TECH_STACK_BADGES}}": build_tech_stack_badges(meta),

        # MERMAID_GRAPH is intentionally NOT html-escaped — Mermaid's JS
        # parser reads the raw text content of the <pre>. Escaping operators
        # like > or -> would break the flowchart syntax.
        "{{MERMAID_GRAPH}}": blueprint.get("mermaid_graph", ""),

        "{{FLOW_CARDS}}":            build_flow_cards(blueprint.get("execution_flow", [])),
        "{{DATA_MODEL_CARDS}}":      build_data_model_cards(blueprint.get("core_data_models", [])),
        "{{DIRECTORY_TABLE_ROWS}}":  build_directory_table_rows(blueprint.get("file_system_directory", [])),
        "{{SETUP_PREREQS}}":         build_setup_prereqs(blueprint.get("setup_and_verification_playbook", {})),
        "{{SETUP_COMMANDS}}":        build_setup_commands(blueprint.get("setup_and_verification_playbook", {})),
    }


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------

def render(blueprint: dict, template: str) -> str:
    """Apply the v1 token set; unknown tokens survive untouched."""
    tokens = build_tokens(blueprint)
    out = template
    for token, value in tokens.items():
        out = out.replace(token, value)
    return out


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    # Accept optional positional arg; fall back to fixture
    blueprint_path = Path(sys.argv[1]) if len(sys.argv) > 1 \
                     else Path("fixtures/callbridge.json")
    template_path  = Path("template.html")
    output_path    = Path("output/architecture_tour.html")

    # Validate inputs
    if not blueprint_path.exists():
        print(f"ERROR: blueprint not found: {blueprint_path}", file=sys.stderr)
        sys.exit(1)
    if not template_path.exists():
        print(f"ERROR: template not found: {template_path}", file=sys.stderr)
        sys.exit(1)

    # Load
    with blueprint_path.open(encoding="utf-8") as f:
        blueprint = json.load(f)
    template = template_path.read_text(encoding="utf-8")

    # Render
    output_html = render(blueprint, template)

    # Write
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(output_html, encoding="utf-8")

    # Report
    meta = blueprint.get("project_metadata", {})
    name = meta.get("name", "(unnamed)")
    print(f"OK Generated: {output_path}")
    print(f"   Project  : {name}")
    print(f"   Blueprint: {blueprint_path}")
    print(f"   Template : {template_path}")


if __name__ == "__main__":
    main()
