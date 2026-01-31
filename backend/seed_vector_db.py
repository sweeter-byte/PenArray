#!/usr/bin/env python3
"""
Seed Vector Database Script for BiZhen Essay System.

This script populates ChromaDB materials_collection with sample
high-quality Chinese quotes, facts, and essay fragments for testing
the RAG pipeline (Librarian agent).

Usage:
    python seed_vector_db.py

Environment Variables:
    CHROMA_HOST: ChromaDB host (default: localhost)
    CHROMA_PORT: ChromaDB port (default: 8000)

Themes covered:
    - Perseverance (坚持/毅力)
    - Innovation (创新)
    - Patriotism (爱国)
"""

import os
import sys
from typing import List, Dict, Any


# Sample high-quality materials for Gaokao essays
SAMPLE_MATERIALS: List[Dict[str, Any]] = [
    # ========== Perseverance (坚持/毅力) ==========
    {
        "id": "quote_perseverance_001",
        "content": "锲而舍之，朽木不折；锲而不舍，金石可镂。——《荀子·劝学》",
        "category": "quote",
        "author": "荀子",
        "tags": ["坚持", "毅力", "学习"],
    },
    {
        "id": "quote_perseverance_002",
        "content": "故天将降大任于斯人也，必先苦其心志，劳其筋骨，饿其体肤。——《孟子》",
        "category": "quote",
        "author": "孟子",
        "tags": ["坚持", "磨练", "成长"],
    },
    {
        "id": "fact_perseverance_001",
        "content": "屠呦呦历经190次失败，终于从青蒿中提取出青蒿素，挽救了数百万疟疾患者的生命，荣获2015年诺贝尔生理学或医学奖。",
        "category": "fact",
        "author": "",
        "tags": ["坚持", "科学", "奉献"],
    },
    {
        "id": "fact_perseverance_002",
        "content": "曹雪芹'批阅十载，增删五次'，穷尽毕生心血创作《红楼梦》，铸就中国古典小说的巅峰之作。",
        "category": "fact",
        "author": "",
        "tags": ["坚持", "文学", "创作"],
    },

    # ========== Innovation (创新) ==========
    {
        "id": "quote_innovation_001",
        "content": "苟日新，日日新，又日新。——《礼记·大学》",
        "category": "quote",
        "author": "礼记",
        "tags": ["创新", "进步", "自我更新"],
    },
    {
        "id": "quote_innovation_002",
        "content": "问渠那得清如许？为有源头活水来。——朱熹《观书有感》",
        "category": "quote",
        "author": "朱熹",
        "tags": ["创新", "学习", "活力"],
    },
    {
        "id": "fact_innovation_001",
        "content": "华为在5G技术领域拥有超过3000项核心专利，坚持每年将10%以上营收投入研发，成为全球5G技术的领导者。",
        "category": "fact",
        "author": "",
        "tags": ["创新", "科技", "自主"],
    },
    {
        "id": "theory_innovation_001",
        "content": "习近平总书记强调：'创新是引领发展的第一动力，抓创新就是抓发展，谋创新就是谋未来。'",
        "category": "theory",
        "author": "习近平",
        "tags": ["创新", "发展", "未来"],
    },

    # ========== Patriotism (爱国) ==========
    {
        "id": "quote_patriotism_001",
        "content": "苟利国家生死以，岂因祸福避趋之。——林则徐",
        "category": "quote",
        "author": "林则徐",
        "tags": ["爱国", "担当", "奉献"],
    },
    {
        "id": "quote_patriotism_002",
        "content": "位卑未敢忘忧国，事定犹须待阖棺。——陆游《病起书怀》",
        "category": "quote",
        "author": "陆游",
        "tags": ["爱国", "责任", "忧患"],
    },
    {
        "id": "fact_patriotism_001",
        "content": "钱学森放弃美国优厚待遇，冲破重重阻挠回到祖国，主持'两弹一星'研制工作，为中国国防事业做出不可磨灭的贡献。",
        "category": "fact",
        "author": "",
        "tags": ["爱国", "奉献", "科学"],
    },
    {
        "id": "literature_patriotism_001",
        "content": "人生自古谁无死？留取丹心照汗青。——文天祥《过零丁洋》",
        "category": "literature",
        "author": "文天祥",
        "tags": ["爱国", "气节", "牺牲"],
    },
]


def get_chroma_settings():
    """Get ChromaDB connection settings from environment or defaults."""
    return {
        "host": os.environ.get("CHROMA_HOST", "localhost"),
        "port": int(os.environ.get("CHROMA_PORT", "8000")),
    }


def seed_vector_database(clear_existing: bool = False):
    """
    Seed the ChromaDB materials_collection with sample materials.

    Args:
        clear_existing: If True, delete existing collection before seeding

    Returns:
        dict: Statistics about the seeding operation
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

        for material in SAMPLE_MATERIALS:
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
                "category": material["category"],
                "author": material["author"],
                "tags": ",".join(material["tags"]),  # Store as comma-separated string
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
    print(f"Materials to seed: {len(SAMPLE_MATERIALS)}")
    print("Themes: Perseverance, Innovation, Patriotism")
    print("=" * 50 + "\n")

    seed_vector_database(clear_existing=args.clear)
