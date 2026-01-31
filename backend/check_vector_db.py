#!/usr/bin/env python3
"""
Check Vector Database Script for BiZhen Essay System.

This script connects to ChromaDB and reports the document count
in the materials_collection used by the Librarian agent (RAG).

Usage:
    python check_vector_db.py

Environment Variables:
    CHROMA_HOST: ChromaDB host (default: localhost)
    CHROMA_PORT: ChromaDB port (default: 8000)
"""

import os
import sys


def get_chroma_settings():
    """Get ChromaDB connection settings from environment or defaults."""
    return {
        "host": os.environ.get("CHROMA_HOST", "localhost"),
        "port": int(os.environ.get("CHROMA_PORT", "8000")),
    }


def check_vector_database():
    """
    Connect to ChromaDB and check the materials_collection.

    Returns:
        dict: Statistics about the collection
    """
    try:
        import chromadb
    except ImportError:
        print("Error: chromadb package not installed.")
        print("Install with: pip install chromadb")
        sys.exit(1)

    settings = get_chroma_settings()
    print(f"Connecting to ChromaDB at {settings['host']}:{settings['port']}...")

    try:
        client = chromadb.HttpClient(
            host=settings["host"],
            port=settings["port"],
        )

        # Test connection by listing collections
        collections = client.list_collections()
        print(f"Connection successful! Found {len(collections)} collection(s).")

        # Get or create the materials_collection
        collection_name = "materials_collection"
        collection = client.get_or_create_collection(collection_name)

        # Get document count
        count = collection.count()

        print("\n" + "=" * 50)
        print(f"Collection: {collection_name}")
        print(f"Total documents: {count}")
        print("=" * 50)

        # If there are documents, show a sample
        if count > 0:
            print("\nSample documents (up to 5):")
            print("-" * 50)

            results = collection.peek(limit=5)

            for i, doc in enumerate(results.get("documents", [])):
                metadata = results["metadatas"][i] if results.get("metadatas") else {}
                category = metadata.get("category", "unknown")
                author = metadata.get("author", "N/A")

                # Truncate long documents for display
                display_doc = doc[:80] + "..." if len(doc) > 80 else doc

                print(f"\n[{i+1}] Category: {category}")
                print(f"    Author: {author}")
                print(f"    Content: {display_doc}")

            # Show category breakdown
            print("\n" + "-" * 50)
            print("Category breakdown:")

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
        else:
            print("\nThe collection is EMPTY!")
            print("Run seed_vector_db.py to add sample materials.")

        return {
            "collection_name": collection_name,
            "total_count": count,
            "status": "connected",
        }

    except Exception as e:
        print(f"\nError connecting to ChromaDB: {e}")
        print("\nTroubleshooting:")
        print("  1. Ensure ChromaDB is running (docker-compose up chroma)")
        print("  2. Check CHROMA_HOST and CHROMA_PORT environment variables")
        print("  3. Verify network connectivity to the ChromaDB service")
        return {
            "status": "error",
            "error": str(e),
        }


if __name__ == "__main__":
    print("BiZhen Vector Database Check")
    print("=" * 50)
    check_vector_database()
