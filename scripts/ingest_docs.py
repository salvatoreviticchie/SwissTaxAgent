"""
Ingest all downloaded tax documents into Pinecone.

Reads docs/manifest.json, extracts text from each file, chunks it,
and upserts into Pinecone using Pinecone Inference (llama-text-embed-v2).

Usage:
    python3 scripts/ingest_docs.py [--docs docs/] [--namespace swiss-tax] [--dry-run]
"""

import argparse
import json
import os
import sys
import time
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from retrieval.document_ingestion import ingest_file
from retrieval.pinecone_retriever import PineconeRetriever
from pinecone import Pinecone


def load_secrets() -> dict:
    secrets_path = Path(__file__).parent.parent / ".streamlit" / "secrets.toml"
    if secrets_path.exists():
        with open(secrets_path, "rb") as f:
            return tomllib.load(f)
    return {}


def get_pc_and_index(index_name: str):
    secrets = load_secrets()
    api_key = os.getenv("PINECONE_API_KEY") or secrets.get("PINECONE_API_KEY", "")
    index_name = os.getenv("PINECONE_INDEX_NAME") or secrets.get("PINECONE_INDEX_NAME", index_name)
    if not api_key:
        raise ValueError("PINECONE_API_KEY not set. Fill .streamlit/secrets.toml")
    pc = Pinecone(api_key=api_key)
    return pc, pc.Index(index_name)


def ingest_all(docs_dir: Path, namespace: str, dry_run: bool = False):
    manifest_path = docs_dir / "manifest.json"
    if not manifest_path.exists():
        print(f"❌ manifest.json not found in {docs_dir}")
        print("   Run: python3 scripts/scrape_vd.py first")
        sys.exit(1)

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    print(f"📋 Manifest: {len(manifest)} items")

    pc = None
    retriever = None
    if not dry_run:
        print("🔌 Connecting to Pinecone…")
        pc, index = get_pc_and_index("rag-docs")
        retriever = PineconeRetriever(index, namespace=namespace)
        retriever.set_pc(pc)
        print("✓ Connected")

    total_chunks = 0
    total_files = 0
    errors = []

    for item in manifest:
        local_path = Path(item["local"])
        if not local_path.exists():
            print(f"  ⚠️  Missing: {local_path.name}")
            errors.append(str(local_path))
            continue

        label = item.get("label") or item.get("name") or local_path.stem
        source_url = item.get("url", "")
        print(f"  ↑ {local_path.name}")

        try:
            chunks = ingest_file(str(local_path), source_name=local_path.name)
            for chunk in chunks:
                chunk["metadata"]["source_url"] = source_url
                chunk["metadata"]["label"] = label
                chunk["metadata"]["category"] = item.get("category", item.get("type", ""))

            if not dry_run and chunks:
                retriever.upsert_chunks(chunks, pc=pc)
                time.sleep(0.3)

            total_chunks += len(chunks)
            total_files += 1
            print(f"     → {len(chunks)} chunks {'(dry run)' if dry_run else 'upserted'}")

        except Exception as e:
            print(f"     ❌ Error: {e}")
            errors.append(f"{local_path.name}: {e}")

    print(f"\n{'[DRY RUN] ' if dry_run else ''}✅ {total_files} files, {total_chunks} chunks → namespace '{namespace}'")
    if errors:
        print(f"⚠️  {len(errors)} errors:")
        for e in errors:
            print(f"   - {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--docs", default="docs")
    parser.add_argument("--namespace", default="swiss-tax")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    docs_dir = Path(__file__).parent.parent / args.docs
    ingest_all(docs_dir, args.namespace, dry_run=args.dry_run)
