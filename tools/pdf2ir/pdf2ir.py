#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    from pdfminer.high_level import extract_text
except Exception:
    extract_text = None

try:
    import fitz  # PyMuPDF
except Exception:
    fitz = None

try:
    from jsonschema import validate, Draft202012Validator, exceptions as jsonschema_exceptions
except Exception:
    validate = None
    Draft202012Validator = None
    jsonschema_exceptions = None

try:
    from rich.console import Console
    from rich.table import Table
    console = Console()
except Exception:
    console = None

STATEMENT_KINDS = ["Definition", "Axiom", "Lemma", "Theorem", "Proposition", "Corollary", "Example", "Assumption"]
COLOR_MODELS = ["RGB","sRGB","XYZ","Lab","LCh","Oklab","OKLCh","LMS","Cone"]
BUILTIN_TYPES = ["Real","Nat","Int","Bool","Vector","Matrix","ColorSpace","Metric","Transform","Cone","Illuminant"]

def log(msg: str):
    if console:
        console.log(msg)
    else:
        print(msg, file=sys.stderr)

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

_id_re = re.compile(r"[^a-z0-9_.-]+")
def make_id(prefix: str, base: str) -> str:
    s = base.strip().lower()
    s = s.replace(" ", "_")
    s = _id_re.sub("", s)
    s = s.strip("._-")
    if not s:
        s = "x"
    # Ensure starts with letter
    if not s[0].isalpha():
        s = "a" + s
    s = f"{prefix}{s[:60]}"
    return s

def canonical_json(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))

def load_schema(schema_path: Path):
    with open(schema_path, "r", encoding="utf-8") as f:
        return json.load(f)

def validate_ir(schema, ir_obj):
    if Draft202012Validator is None:
        log("jsonschema not available; skipping validation")
        return True, []
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(ir_obj), key=lambda e: list(e.path))
    if errors:
        msgs = []
        for e in errors:
            loc = "$." + ".".join(str(p) for p in e.path)
            msgs.append(f"{loc}: {e.message}")
        return False, msgs
    return True, []

def extract_text_fallback(pdf_path: Path) -> str:
    # Prefer pdfminer for robust text layout
    if extract_text:
        try:
            return extract_text(str(pdf_path)) or ""
        except Exception as e:
            log(f"[warn] pdfminer extract failed: {e}")
    # Fallback to PyMuPDF simple text extraction
    if fitz:
        try:
            text_chunks = []
            with fitz.open(str(pdf_path)) as doc:
                for page in doc:
                    text_chunks.append(page.get_text())
            return "\n".join(text_chunks)
        except Exception as e:
            log(f"[warn] PyMuPDF extract failed: {e}")
    return ""

def parse_sections(text: str):
    # Minimal: create one root section, plus simple detection of headings like "1 Title" or "1.1 Subtitle"
    lines = text.splitlines()
    secs = []
    order = 0
    for ln in lines[:200]:
        if re.match(r"^\s*\d+(\.\d+)*\s+\S+", ln):
            title = ln.strip()
            secs.append({"id": make_id("s_", title), "title": title, "order": order})
            order += 1
    if not secs:
        secs = [{"id": "s_root", "title": "Root", "order": 0}]
    return secs

def parse_statements(text: str):
    stmts = []
    pattern = re.compile(r"^\s*(Definition|Axiom|Lemma|Theorem|Proposition|Corollary|Example|Assumption)\b[.:]?\s*(.*)$", re.IGNORECASE)
    seen_ids = set()

    def unique_stmt_id(kind: str, label: str) -> str:
        base = make_id("t_", f"{kind}_{label}")
        cand = base
        n = 2
        while cand in seen_ids:
            cand = f"{base}_{n}"
            n += 1
        seen_ids.add(cand)
        return cand

    for i, ln in enumerate(text.splitlines()):
        m = pattern.match(ln)
        if m:
            kind = m.group(1).capitalize()
            rest = m.group(2).strip()
            label = (rest[:80] or f"{kind} at line {i+1}").strip()
            sid = unique_stmt_id(kind, label)
            stmts.append({
                "id": sid,
                "kind": kind if kind in STATEMENT_KINDS else "Assumption",
                "label": label,
                "text": ln.strip(),
                "html": "",
                "confidence": 0.6,
                "math_blocks": [],
                "symbols_declared": [],
                "symbols_used": [],
                "deps": [],
                "params": [],
            })
    if not stmts:
        sid = unique_stmt_id("Assumption", "DocumentPlaceholder")
        stmts = [{
            "id": sid,
            "kind": "Assumption",
            "label": "DocumentPlaceholder",
            "text": "Placeholder statement (no labeled statements detected).",
            "html": "",
            "confidence": 0.1,
            "math_blocks": [],
            "symbols_declared": [],
            "symbols_used": [],
            "deps": [],
            "params": [],
        }]
    return stmts

def derive_symbols_from_text(text: str, statements):
    # Heuristic: collect capitalized tokens as candidate symbols
    tokens = re.findall(r"\b([A-Z][A-Za-z0-9]{2,})\b", text)
    seen = set()
    symbols = []
    for t in tokens[:20]:
        if t.lower() in seen:
            continue
        seen.add(t.lower())
        sym_id = make_id("y_", t)
        symbols.append({
            "id": sym_id,
            "name": t,
            "unicode": t,
            "aliases": [],
            "role": "Constant",
            "arity": 0,
            "type_expr": "Type",
            "coq_sort": "Type",
            "defined_by": statements[0]["id"] if statements else None,
            "scope": "document",
            "normalization": {
                "canonical_name": t,
                "ascii_fallback": t
            }
        })
    if not symbols:
        symbols = [{
            "id": "y_doc",
            "name": "DocSymbol",
            "unicode": "DocSymbol",
            "aliases": [],
            "role": "Constant",
            "arity": 0,
            "type_expr": "Type",
            "coq_sort": "Type",
            "defined_by": statements[0]["id"] if statements else None,
            "scope": "document",
            "normalization": {"canonical_name": "DocSymbol", "ascii_fallback": "DocSymbol"}
        }]
    return symbols

def normalize_name_for_canonical(name: str) -> str:
    # Produce ^[A-Za-z][A-Za-z0-9._]*$ from an arbitrary display name
    s = name.strip()
    s = re.sub(r"[\\s\\-]+", ".", s)  # join words with dots for namespacing
    s = re.sub(r"[^A-Za-z0-9._]", "", s)  # drop unsupported chars
    s = s.strip(".")
    if not s:
        s = "S"
    if not re.match(r"^[A-Za-z]", s):
        s = "S" + s
    return s

def normalize_symbols(ir: dict) -> None:
    seen_ascii = set()
    for sym in ir.get("symbols", []):
        norm = sym.get("normalization") or {}
        cname = normalize_name_for_canonical(norm.get("canonical_name") or sym.get("name", "S"))
        af = normalize_name_for_canonical(norm.get("ascii_fallback") or cname)
        base = af
        n = 2
        while af in seen_ascii:
            af = f"{base}_{n}"
            n += 1
        seen_ascii.add(af)
        sym["normalization"] = {
            "canonical_name": cname,
            "ascii_fallback": af
        }
        if sym.get("scope") not in ("document", "section", "statement"):
            sym["scope"] = "document"

def annotate_symbols_used(ir: dict) -> None:
    # Map symbol textual keys to ids (name, canonical, ascii_fallback)
    syms = ir.get("symbols", [])
    sym_names = {}
    for s in syms:
        sym_names.setdefault(s.get("name", ""), []).append(s["id"])
        nrm = s.get("normalization", {})
        sym_names.setdefault(nrm.get("ascii_fallback", ""), []).append(s["id"])
        sym_names.setdefault(nrm.get("canonical_name", ""), []).append(s["id"])
    # Heuristic: match by word boundary in label+text
    for st in ir.get("statements", []):
        used = set(st.get("symbols_used", []))
        blob = f"{st.get('label','')} {st.get('text','')}"
        for key, ids in sym_names.items():
            if not key:
                continue
            if re.search(rf"\\b{re.escape(key)}\\b", blob):
                for sid in ids:
                    used.add(sid)
        st["symbols_used"] = list(used)

def build_dependency_graph(doc_id: str, sections, statements, symbols):
    # Build unique nodes and infer usesSymbol edges from statements.symbols_used
    nodes_map = {}
    def add_node(node_id, kind, label):
        nodes_map[node_id] = {"id": node_id, "kind": kind, "label": label}
    add_node(doc_id, "Document", doc_id)
    for s in sections:
        add_node(s["id"], "Section", s.get("title", ""))
    for t in statements:
        add_node(t["id"], "Statement", t.get("label", ""))
    for y in symbols:
        add_node(y["id"], "Symbol", y.get("name", ""))
    edges = []
    for t in statements:
        for sid in t.get("symbols_used", []):
            edges.append({"from": t["id"], "to": sid, "type": "usesSymbol"})
        for dep in t.get("deps", []):
            tgt = dep.get("target")
            ety = dep.get("edge_type", "dependsOn")
            if tgt:
                edges.append({"from": t["id"], "to": tgt, "type": ety})
    return {"nodes": list(nodes_map.values()), "edges": edges}

def nlp_normalize(ir: dict) -> None:
    # Canonicalize symbols, annotate per-statement symbol usage, rebuild dependency graph
    normalize_symbols(ir)
    annotate_symbols_used(ir)
    doc_id = ir["document"]["id"]
    ir["dependency_graph"] = build_dependency_graph(
        doc_id, ir.get("sections", []), ir.get("statements", []), ir.get("symbols", [])
    )

def make_tool_versions():
    return {
        "pdf_parser": "pdfminer" if extract_text else ("pymupdf" if fitz else "none"),
        "nlp_normalizer": "builtin",
        "ir_to_coq": "N/A",
        "coq": "8.19",
        "ocaml": "5.x",
        "dune": "3.x"
    }

def build_ir(pdf_path: Path, schema) -> dict:
    text = extract_text_fallback(pdf_path)
    sections = parse_sections(text)
    statements = parse_statements(text)
    symbols = derive_symbols_from_text(text, statements)
    doc_id = make_id("d_", pdf_path.stem)
    ir = {
        "ir_version": "1.0.0",
        "document": {
            "id": doc_id,
            "title": pdf_path.stem,
            "source_path": str(pdf_path.as_posix()),
            "sha256": sha256_file(pdf_path),
            "created_at": now_iso(),
            "tool_versions": make_tool_versions(),
            "sections": [s["id"] for s in sections],
            "bibliography": [],
            "glossary": []
        },
        "sections": sections,
        "statements": statements,
        "symbols": symbols,
        "typesystem": {
            "builtin_types": BUILTIN_TYPES,
            "numeric_repr": "exact_rational",
            "policy": {
                "store_original_decimal": True,
                "rational_approx": {"max_den": 1000, "method": "contfrac"}
            }
        },
        "geometry_domain": {
            "color_models": COLOR_MODELS,
            "transforms": [],
            "metrics": []
        },
        "dependency_graph": {"nodes": [], "edges": []},
        "coq_mappings": [],
        "build_meta": {
            "ir_version": "1.0.0",
            "reproducibility_digest": "0"*64,
            "tool_versions": make_tool_versions(),
            "build_profile": "debug",
            "wasm_runtime": "ocamlrun"
        }
    }
    # NLP normalization: canonicalize symbols, annotate symbol usage, and rebuild dependency graph
    nlp_normalize(ir)
    ok, errs = validate_ir(schema, ir)
    if not ok:
        log("[error] IR failed schema validation pre-digest:")
        for m in errs[:10]:
            log("  " + m)
    # Compute digest over canonical form excluding reproducibility_digest itself by zeroing it
    s = canonical_json(ir)
    digest = hashlib.sha256(s.encode("utf-8")).hexdigest()
    ir["build_meta"]["reproducibility_digest"] = digest
    ok, errs = validate_ir(schema, ir)
    if not ok:
        log("[error] IR failed schema validation:")
        for m in errs[:50]:
            log("  " + m)
        raise SystemExit(2)
    return ir

def write_json(path: Path, obj: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
        f.write("\n")

# New Markdown/report utilities

def kebab_case(name: str) -> str:
    """Normalize a string into kebab-case suitable for filenames."""
    s = name.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s or "x"

def compute_tags(title: str) -> list:
    """Heuristically derive tags from the title; always includes 'reports'."""
    l = (title or "").lower()
    tags = []
    def add_tag(t: str):
        if t not in tags:
            tags.append(t)
    add_tag("reports")
    if "axiom" in l:
        add_tag("axioms"); add_tag("neurosymbolic"); add_tag("color-geometry")
    if "conceptual" in l:
        add_tag("conceptual-spaces"); add_tag("theory")
    if "causality" in l or "snn" in l:
        add_tag("snn"); add_tag("causality")
    if "symbol grounding" in l:
        add_tag("symbol-grounding"); add_tag("color-geometry")
    if "web app" in l or "oklab web app" in l:
        add_tag("webapp"); add_tag("oklab"); add_tag("semantics")
    return tags

def build_report_front_matter(title: str, source_pdf_rel: str, tags: list, description: str = None) -> str:
    """Build reusable YAML front-matter for a report markdown file."""
    desc = description or "Auto-generated report from PDF"
    today = datetime.now().strftime("%Y-%m-%d")
    # Ensure 'reports' is first and unique
    uniq = []
    for t in (tags or []):
        if t not in uniq:
            uniq.append(t)
    if "reports" not in uniq:
        uniq.insert(0, "reports")
    else:
        # move to front if not already
        uniq = ["reports"] + [t for t in uniq if t != "reports"]
    tags_inline = ", ".join(uniq)
    fm = []
    fm.append("---")
    fm.append(f"title: {title}")
    fm.append(f"description: {desc}")
    fm.append(f"tags: [{tags_inline}]")
    fm.append(f"source-pdf: {source_pdf_rel}")
    fm.append(f"last-updated: {today}")
    fm.append("---")
    return "\n".join(fm) + "\n"

def suggest_cross_links(title: str) -> list:
    """Suggest related documentation links based on the title."""
    l = (title or "").lower()
    # repository-relative candidates
    links = set()
    # Base mapping universe
    CG = "docs/theory/color-geometry.md"
    CS = "docs/theory/conceptual-spaces.md"
    AX = "docs/advanced/axioms-and-neurosymbolics.md"
    CA = "docs/advanced/causality-in-snn.md"
    OK = "docs/advanced/oklab-geometric-semantics.md"
    WA = "docs/implementations/webapp/overview.md"
    IR = "docs/methods/cgir-ir.md"
    VV = "docs/methods/verification-and-validation.md"
    NC = "docs/theory/neurons-and-causality.md"
    SG = "docs/foundations/symbol-grounding-basics.md"
    if "axiom" in l:
        links.add(CG); links.add(AX)
    if "conceptual spaces" in l or "conceptual-spaces" in l:
        links.add(CS)
    if "snn" in l or "causality" in l:
        links.add(NC); links.add(CA)
    if "symbol grounding" in l:
        links.add(SG); links.add(CG)
    if "web app" in l or "oklab web app" in l:
        links.add(WA); links.add(OK)
    # Optionally include method docs when color geometry context is likely
    if "color" in l or "geometry" in l:
        links.add(IR); links.add(VV)
    return [p for p in links]

def extract_figures_with_pymupdf(pdf_path: Path, out_dir: Path, base: str) -> list:
    """Extract embedded images using PyMuPDF into out_dir/base_*.png. Returns list of dicts with abs_path, caption, page."""
    results = []
    if fitz is None:
        return results
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        with fitz.open(str(pdf_path)) as doc:
            for pno, page in enumerate(doc, start=1):
                try:
                    image_list = page.get_images(full=True)
                except Exception:
                    image_list = []
                for idx, img in enumerate(image_list, start=1):
                    try:
                        xref = img[0]
                        pix = fitz.Pixmap(doc, xref)
                        # Handle CMYK and alpha channels
                        if pix.n > 4:
                            pix = fitz.Pixmap(fitz.csRGB, pix)
                        if getattr(pix, "alpha", 0):
                            pix = fitz.Pixmap(pix, 0)  # remove alpha
                        fname = f"{base}_p{pno}_i{idx}.png"
                        out_path = out_dir / fname
                        pix.save(str(out_path))
                        results.append({"abs_path": str(out_path), "caption": f"Figure p{pno} i{idx}", "page": pno})
                    except Exception:
                        # continue extracting others
                        continue
    except Exception as e:
        log(f"[warn] Failed figure extraction on {pdf_path}: {e}")
    return results

def write_markdown_report(md_path: Path, title: str, pdf_path: Path, extracted_text: str, cross_links: list, figures: list):
    """Write a structured Markdown report aligning with the documentation plan."""
    md_path.parent.mkdir(parents=True, exist_ok=True)
    # Front-matter
    tags = compute_tags(title)
    source_pdf_rel = f"pdf/{pdf_path.name}"
    fm = build_report_front_matter(title=title, source_pdf_rel=source_pdf_rel, tags=tags)
    # Abstract
    abstract = ""
    if extracted_text:
        words = re.findall(r"\S+", extracted_text.replace("\n", " "))
        abstract = " ".join(words[:100])
    if not abstract:
        abstract = "This abstract is a placeholder. Content will be curated from the source PDF."
    # Key concepts from detected section titles
    try:
        secs = parse_sections(extracted_text or "")
    except Exception:
        secs = [{"title":"Root"}]
    key_concepts = [s.get("title","").strip() for s in secs[:5] if s.get("title")]
    if not key_concepts:
        key_concepts = ["TBD – curate key concepts."]
    # Methods and Results stubs
    methods = [
        "Auto-generated summary from initial PDF text extraction.",
        "Review and curate identified statements and sections.",
        "Relate methods to Color Geometry and CGIR where applicable.",
        "Validate and verify claims; link to proofs or simulations when available.",
        "Summarize results and implications."
    ]
    # Figures section
    fig_lines = []
    for f in (figures or []):
        cap = f.get("caption") or "Figure"
        p = f.get("path") or ""
        fig_lines.append(f"![{cap}]({p})")
    if not fig_lines:
        fig_lines = ["(No figures extracted. Enable --extract-figures with PyMuPDF available to include embedded images.)"]
    # Cross-links
    clinks = []
    # Convert repository-relative 'docs/...' to path relative to md_path.parent
    for link in (cross_links or []):
        try:
            rel = os.path.relpath(link, start=str(md_path.parent))
        except Exception:
            rel = link
        clinks.append(f"- [{link}]({rel})")
    if not clinks:
        clinks = ["- (No suggested cross-links)"]
    # Reference to source PDF relative from md to repo root
    ref_pdf_rel = os.path.relpath(f"pdf/{pdf_path.name}", start=str(md_path.parent))
    back_to_index_rel = os.path.relpath("docs/README.md", start=str(md_path.parent))
    # Compose document
    parts = []
    parts.append(fm)
    parts.append(f"# {title}")
    parts.append("")
    parts.append("## Abstract")
    parts.append(abstract)
    parts.append("")
    parts.append("## Key Concepts")
    parts.extend([f"- {t}" for t in key_concepts])
    parts.append("")
    parts.append("## Methods and Results")
    parts.extend([f"- {m}" for m in methods])
    parts.append("")
    parts.append("## Figures")
    parts.extend(fig_lines)
    parts.append("")
    parts.append("## Cross-Links")
    parts.extend(clinks)
    parts.append("")
    parts.append("## References")
    parts.append(f"- Source PDF: [{pdf_path.name}]({ref_pdf_rel})")
    parts.append("")
    parts.append(f"Back to index: [docs/README.md]({back_to_index_rel})")
    parts.append("")
    parts.append("_Note: Paths assume repository-relative navigation from within the docs/ tree._")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(parts) + "\n")

def main():
    ap = argparse.ArgumentParser(description="Parse PDFs into Color Geometry IR JSON")
    # Existing flags
    ap.add_argument("--in", dest="inp", default="pdf", help="Input directory with PDFs")
    ap.add_argument("--out", dest="out", default="build/ir", help="Output directory for IR JSON files")
    ap.add_argument("--schema", dest="schema", default="docs/ir/ir-schema.json", help="Path to IR JSON Schema")
    # New flags for Markdown and figures
    ap.add_argument("--md-out", dest="md_out", default="docs/reports", help="Directory to write Markdown reports (default: docs/reports)")
    ap.add_argument("--emit-markdown", dest="emit_markdown", action="store_true", help="Emit Markdown reports in addition to IR JSON")
    ap.add_argument("--extract-figures", dest="extract_figures", action="store_true", help="Extract embedded figures (PyMuPDF required)")
    ap.add_argument("--img-out", dest="img_out", default="docs/img/reports", help="Directory to write extracted figures (default: docs/img/reports)")
    ap.add_argument("--kebab-names", dest="kebab_names", action="store_true", default=True, help="Normalize report filenames using kebab-case (default: enabled)")
    ap.add_argument("--no-kebab-names", dest="kebab_names", action="store_false", help="Disable kebab-case normalization for report filenames")
    args = ap.parse_args()

    in_dir = Path(args.inp)
    out_dir = Path(args.out)
    schema_path = Path(args.schema)
    md_out_dir = Path(args.md_out)
    img_out_dir = Path(args.img_out)

    if not in_dir.exists():
        log(f"[error] Input directory not found: {in_dir}")
        return 1

    # Determine whether to emit Markdown even if --emit-markdown not explicitly set but --md-out was provided.
    md_flag_present = any(a == "--emit-markdown" for a in sys.argv[1:]) or any(a.startswith("--md-out") for a in sys.argv[1:])
    emit_md = bool(args.emit_markdown or md_flag_present)

    # Load schema if present; allow markdown-only mode when schema missing/invalid
    schema = None
    if schema_path.exists():
        try:
            schema = load_schema(schema_path)
        except Exception as e:
            log(f"[warn] Failed to load schema '{schema_path}': {e}. Proceeding without validation.")
            schema = None
    else:
        if not emit_md:
            log(f"[error] Schema not found: {schema_path}")
            return 1
        log(f"[warn] Schema not found: {schema_path}. Proceeding with Markdown generation only.")

    pdfs = sorted([p for p in in_dir.iterdir() if p.suffix.lower() == ".pdf"])
    if not pdfs:
        log(f"[warn] No PDFs found in {in_dir}")

    if emit_md:
        md_out_dir.mkdir(parents=True, exist_ok=True)
    if args.extract_figures and fitz is None:
        log("[warn] --extract-figures requested but PyMuPDF (fitz) is not available. Skipping image extraction.")

    ok_count = 0
    md_count = 0
    for pdf in pdfs:
        log(f"Processing {pdf} ...")
        # Extract text best-effort (for Markdown generation and for IR)
        extracted_text = ""
        try:
            extracted_text = extract_text_fallback(pdf)
        except Exception as e:
            log(f"[warn] Text extraction failed on {pdf}: {e}")

        # Build IR JSON when schema is available
        ir = None
        if schema is not None:
            try:
                ir = build_ir(pdf, schema)
            except SystemExit:
                # build_ir may exit on schema validation failure; continue to Markdown generation
                log(f"[error] IR build failed on {pdf} (schema validation). Continuing with Markdown.")
            except Exception as e:
                log(f"[error] IR build failed on {pdf}: {e}")

        # Write IR JSON if built
        if ir is not None:
            try:
                out_path = out_dir / (pdf.stem + ".json")  # keep verbatim stem per existing behavior
                write_json(out_path, ir)
                ok_count += 1
            except Exception as e:
                log(f"[error] Failed to write IR JSON for {pdf}: {e}")

        # Markdown generation (additive to IR)
        if emit_md:
            try:
                title = pdf.stem
                base_name = kebab_case(title) if args.kebab_names else title
                md_filename = f"{base_name}.md" if not base_name.endswith(".md") else base_name
                md_path = md_out_dir / md_filename

                # Extract figures if requested and fitz available
                figures = []
                if args.extract_figures and fitz is not None:
                    # put figures under img_out/<base>/
                    base_dir = kebab_case(title) if args.kebab_names else title
                    img_subdir = img_out_dir / base_dir
                    extracted = extract_figures_with_pymupdf(pdf, img_subdir, base_dir)
                    for item in extracted:
                        # path relative to the markdown file location
                        rel = os.path.relpath(item["abs_path"], start=str(md_out_dir))
                        figures.append({"path": rel, "caption": item.get("caption", "Figure"), "page": item.get("page")})

                # Cross-links (repository-relative); write_markdown_report will relativize them
                links = suggest_cross_links(title)

                write_markdown_report(md_path, title, pdf, extracted_text or "", links, figures)
                md_count += 1
                log(f"[info] Wrote report: {md_path}")
            except Exception as e:
                log(f"[warn] Failed to write Markdown report for {pdf}: {e}")

    log(f"Done. Wrote {ok_count} IR files to {out_dir}")
    if emit_md:
        log(f"Done. Wrote {md_count} Markdown reports to {md_out_dir}")
    return 0

if __name__ == "__main__":
    sys.exit(main())