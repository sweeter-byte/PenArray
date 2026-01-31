#!/usr/bin/env python3
"""
Seed Vector Database Script for BiZhen Essay System.

This script populates ChromaDB materials_collection with sample
high-quality Chinese quotes, facts, and essay fragments for testing
the RAG pipeline (Librarian agent).

Usage:
    python seed_vector_db.py
    python seed_vector_db.py --clear  # Clear and reseed

Environment Variables:
    CHROMA_HOST: ChromaDB host (default: localhost)
    CHROMA_PORT: ChromaDB port (default: 8000)

Data Source:
    backend/data/materials.json - JSON file containing essay materials
"""

import json
import os
import sys
from pathlib import Path
from typing import List, Dict, Any


def load_materials_from_json() -> List[Dict[str, Any]]:
    """
    Load materials from the JSON data file.

    Returns:
        List of material dictionaries

    Raises:
        FileNotFoundError: If materials.json doesn't exist
        json.JSONDecodeError: If JSON is invalid
    """
    # Get the path to materials.json relative to this script
    script_dir = Path(__file__).parent
    json_path = script_dir / "data" / "materials.json"

    if not json_path.exists():
        print(f"Error: Materials file not found at {json_path}")
        print("Please create backend/data/materials.json with essay materials.")
        sys.exit(1)

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        materials = data.get("materials", [])
        print(f"Loaded {len(materials)} materials from {json_path}")

        # Show theme breakdown
        themes = {}
        for m in materials:
            theme = m.get("theme", "unknown")
            themes[theme] = themes.get(theme, 0) + 1

        print("Theme distribution:")
        for theme, count in sorted(themes.items()):
            print(f"  - {theme}: {count}")

        return materials

    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {json_path}: {e}")
        sys.exit(1)
    except UnicodeDecodeError as e:
        print(f"Error: Unicode encoding issue in {json_path}: {e}")
        print("Ensure the file is saved with UTF-8 encoding.")
        sys.exit(1)


# Load materials from JSON file
SAMPLE_MATERIALS: List[Dict[str, Any]] = []


def get_chroma_settings():
    """Get ChromaDB connection settings from environment or defaults."""
    return {
        "host": os.environ.get("CHROMA_HOST", "localhost"),
        "port": int(os.environ.get("CHROMA_PORT", "8000")),
    }


def seed_vector_database(clear_existing: bool = False, materials: List[Dict[str, Any]] = None):
    """
    Seed the ChromaDB materials_collection with sample materials.

    Args:
        clear_existing: If True, delete existing collection before seeding
        materials: List of material dictionaries to seed (loaded from JSON)

    Returns:
        dict: Statistics about the seeding operation
    """
    if materials is None:
        materials = load_materials_from_json()

    try:
        import chromadb
    except ImportError:
        print("Error: chromadb package not installed.")
        print("Install with: pip install chromadb")
        sys.exit(1)

    settings = get_chroma_settings()
    print(f"\nConnecting to ChromaDB at {settings['host']}:{settings['port']}...")

    try:
        client = chromadb.HttpClient(
            host=settings["host"],
            port=settings["port"],
        )

        collection_name = "materials_collection"

        # Optionally clear existing collection
        if clear_existing:
            try:
                client.delete_collection(collection_name)
                print(f"Deleted existing collection: {collection_name}")
            except Exception:
                pass  # Collection doesn't exist

        # Get or create collection (uses ChromaDB default embedding)
        collection = client.get_or_create_collection(collection_name)

        existing_count = collection.count()
        print(f"Existing documents in collection: {existing_count}")

        # Prepare data for batch insertion
        ids = []
        documents = []
        metadatas = []

        for material in materials:
            # Check if document already exists
            try:
                existing = collection.get(ids=[material["id"]])
                if existing and existing.get("ids"):
                    print(f"  Skipping existing: {material['id']}")
                    continue
            except Exception:
                pass  # Document doesn't exist, proceed to add

            ids.append(material["id"])
            documents.append(material["content"])
            metadatas.append({
                "category": material.get("category", "unknown"),
                "author": material.get("author", ""),
                "tags": ",".join(material.get("tags", [])),  # Store as comma-separated string
                "theme": material.get("theme", ""),  # Include theme for filtering
            })

        if not ids:
            print("\nAll materials already exist in the collection.")
            return {
                "added": 0,
                "total": collection.count(),
            }

        # Add documents to collection
        print(f"\nAdding {len(ids)} new documents...")
        collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
        )

        new_count = collection.count()
        added = new_count - existing_count

        print("\n" + "=" * 50)
        print("Seeding Complete!")
        print("=" * 50)
        print(f"Documents added: {added}")
        print(f"Total documents: {new_count}")
        print("=" * 50)

        # Show category breakdown
        print("\nCategory breakdown:")
        for category in ["quote", "fact", "theory", "literature"]:
            try:
                cat_results = collection.get(
                    where={"category": category},
                    limit=1000,
                )
                cat_count = len(cat_results.get("ids", []))
                print(f"  - {category}: {cat_count} document(s)")
            except Exception:
                print(f"  - {category}: (unable to query)")

        # Test a sample query
        print("\n" + "-" * 50)
        print("Testing RAG query: '坚持不懈的例子'")
        print("-" * 50)

        results = collection.query(
            query_texts=["坚持不懈的例子"],
            n_results=3,
        )

        for i, doc in enumerate(results.get("documents", [[]])[0]):
            metadata = results["metadatas"][0][i] if results.get("metadatas") else {}
            category = metadata.get("category", "unknown")
            display_doc = doc[:60] + "..." if len(doc) > 60 else doc
            print(f"  [{i+1}] ({category}) {display_doc}")

        return {
            "added": added,
            "total": new_count,
        }

    except Exception as e:
        print(f"\nError seeding ChromaDB: {e}")
        print("\nTroubleshooting:")
        print("  1. Ensure ChromaDB is running (docker-compose up chroma)")
        print("  2. Check CHROMA_HOST and CHROMA_PORT environment variables")
        print("  3. Verify network connectivity to the ChromaDB service")
        return {
            "status": "error",
            "error": str(e),
        }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Seed BiZhen vector database with sample materials"
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear existing collection before seeding",
    )
    args = parser.parse_args()

    print("BiZhen Vector Database Seeding")
    print("=" * 50)

    # Load materials from JSON file
    materials = load_materials_from_json()

    print("=" * 50)

    seed_vector_database(clear_existing=args.clear, materials=materials)
