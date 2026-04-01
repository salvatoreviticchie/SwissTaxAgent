"""
Scrape and download all 2025 Swiss tax documents from vd.ch and estv.admin.ch.

Usage:
    python3 scripts/scrape_vd.py [--output docs/]

Downloads into:
    docs/
    ├── instructions/      # General + complementary instructions
    ├── forms/             # Declaration forms and annexes
    ├── baremes/           # Tax rate tables
    ├── deductions/        # Deduction tables
    ├── pages/             # Full text of key web pages (as .txt)
    └── manifest.json      # All downloaded files + source URLs
"""

import argparse
import json
import os
import re
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

BASE_VD = "https://www.vd.ch"
BASE_ESTV = "https://www.estv.admin.ch"

# Key pages to scrape for text content
TEXT_PAGES = {
    "individus_overview": f"{BASE_VD}/etat-droit-finances/impots/impots-pour-les-individus",
    "deductions": f"{BASE_VD}/etat-droit-finances/impots/impots-pour-les-individus/les-deductions",
    "calendrier": f"{BASE_VD}/etat-droit-finances/impots/impots-pour-les-individus/calendrier-fiscal-2024",
    "situation_personnelle": f"{BASE_VD}/etat-droit-finances/impots/impots-pour-les-individus/ma-situation-personnelle",
    "types_impots": f"{BASE_VD}/etat-droit-finances/impots/impots-pour-les-individus/les-impots-les-differents-types-dimpots",
    "pieces_justificatives": f"{BASE_VD}/etat-droit-finances/impots/impots-pour-les-individus/les-pieces-justificatives",
    "formulaires_baremes": f"{BASE_VD}/etat-droit-finances/impots/formulaires-directives-et-baremes",
    "payer_impots": f"{BASE_VD}/etat-droit-finances/impots/impots-pour-les-individus/payer-mes-impots",
}

# Priority PDFs — 2025 documents only (current tax year)
PDF_ALLOWLIST = [
    # Instructions
    "21001_2025",           # Instructions générales
    "21003_2025",           # Instructions indépendants
    "21004_2025",           # Instructions propriété immobilière
    "21005_2025",           # Instructions exploitants du sol
    # Forms
    "0210_21010_2025",      # Déclaration revenu et fortune
    "0220_21014_2025",      # Annexe 1: Etat des titres
    "0310_21016_01-1_2025", # Annexe 01-1: Participations qualifiées
    "0330_21018_21019_2025",# Annexes 2 et 3
    "0240_21024_22025_2025",# Annexes 4 et 5: Frais professionnels, médicaux, dons
    "0320_21028_21028_2025",# Annexe 7: Immeuble
    "21030_2025",           # Immeubles agricoles
    # Deductions + misc
    "Tableau_des_d",        # Tableau des déductions 2025
    "21013-3",              # Notice sapeurs-pompiers
    "21029_01_49",          # Déclaration prestation en capital
    "30025_deter_modif",    # Acomptes
    # Barèmes (no year in filename, always current)
    "bareme", "Bareme", "coefficients", "Circulaire",
]


def is_wanted_pdf(url: str) -> bool:
    return any(key in url for key in PDF_ALLOWLIST)


def clean_text(soup: BeautifulSoup) -> str:
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    main = soup.find("main") or soup.find(id="main") or soup
    return re.sub(r"\s{3,}", "\n\n", main.get_text(separator="\n", strip=True))


def fetch(client: httpx.Client, url: str) -> httpx.Response | None:
    try:
        r = client.get(url, follow_redirects=True, timeout=20)
        r.raise_for_status()
        return r
    except Exception as e:
        print(f"  ⚠️  Failed {url}: {e}")
        return None


def pdf_filename(url: str) -> str:
    name = Path(urlparse(url).path).name
    # URL-decode percent-encoding
    from urllib.parse import unquote
    return unquote(name)


def categorise(filename: str) -> str:
    fn = filename.lower()
    if any(x in fn for x in ["21001", "21003", "21004", "21005", "instruction"]):
        return "instructions"
    if any(x in fn for x in ["bareme", "coefficients", "circulaire"]):
        return "baremes"
    if any(x in fn for x in ["deduction", "tableau_des_d"]):
        return "deductions"
    return "forms"


def scrape(output_dir: Path):
    output_dir.mkdir(parents=True, exist_ok=True)
    for sub in ["instructions", "forms", "baremes", "deductions", "pages"]:
        (output_dir / sub).mkdir(exist_ok=True)

    manifest = []

    with httpx.Client(
        headers={"User-Agent": "SwissTaxAgent-Scraper/1.0 (research project)"},
        timeout=30,
    ) as client:

        # ── 1. Scrape text pages ─────────────────────────────────────────────
        print("\n📄 Scraping text pages…")
        for name, url in TEXT_PAGES.items():
            print(f"  {name} — {url}")
            resp = fetch(client, url)
            if not resp:
                continue
            soup = BeautifulSoup(resp.text, "html.parser")
            text = clean_text(soup)
            out_path = output_dir / "pages" / f"{name}.txt"
            out_path.write_text(text, encoding="utf-8")
            manifest.append({"type": "page", "name": name, "url": url, "local": str(out_path)})
            time.sleep(0.5)

        # ── 2. Collect all PDF links from formulaires page ───────────────────
        print("\n🔍 Collecting PDF links from formulaires page…")
        forms_url = f"{BASE_VD}/etat-droit-finances/impots/formulaires-directives-et-baremes"
        resp = fetch(client, forms_url)
        pdf_links = {}
        if resp:
            soup = BeautifulSoup(resp.text, "html.parser")
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if ".pdf" in href.lower():
                    full_url = urljoin(BASE_VD, href) if href.startswith("/") else href
                    label = a.get_text(strip=True) or Path(href).stem
                    pdf_links[full_url] = label

        # Also check individuals page for direct PDF links
        resp2 = fetch(client, f"{BASE_VD}/etat-droit-finances/impots/impots-pour-les-individus")
        if resp2:
            soup2 = BeautifulSoup(resp2.text, "html.parser")
            for a in soup2.find_all("a", href=True):
                href = a["href"]
                if ".pdf" in href.lower():
                    full_url = urljoin(BASE_VD, href) if href.startswith("/") else href
                    label = a.get_text(strip=True) or Path(href).stem
                    pdf_links.setdefault(full_url, label)

        print(f"  Found {len(pdf_links)} PDF links total")

        # ── 3. Download wanted PDFs ──────────────────────────────────────────
        print("\n⬇️  Downloading PDFs…")
        downloaded = 0
        skipped = 0
        for url, label in pdf_links.items():
            if not is_wanted_pdf(url):
                skipped += 1
                continue
            filename = pdf_filename(url)
            category = categorise(filename)
            out_path = output_dir / category / filename
            if out_path.exists():
                print(f"  ✓ already exists: {filename}")
                manifest.append({"type": "pdf", "category": category, "label": label, "url": url, "local": str(out_path)})
                downloaded += 1
                continue
            print(f"  ↓ {filename}")
            resp = fetch(client, url)
            if resp and resp.headers.get("content-type", "").startswith("application/pdf"):
                out_path.write_bytes(resp.content)
                manifest.append({"type": "pdf", "category": category, "label": label, "url": url, "local": str(out_path)})
                downloaded += 1
            else:
                print(f"    ⚠️  Not a PDF or failed: {url}")
            time.sleep(0.3)

        print(f"\n  Downloaded: {downloaded} | Skipped (old/unwanted): {skipped}")

    # ── 4. Write manifest ────────────────────────────────────────────────────
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n✅ Done. Manifest: {manifest_path}")
    print(f"   Total items: {len(manifest)}")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape Vaud tax documents")
    parser.add_argument("--output", default="docs", help="Output directory (default: docs/)")
    args = parser.parse_args()

    output_dir = Path(__file__).parent.parent / args.output
    scrape(output_dir)
