#!/usr/bin/env python3
"""
Test script to verify the dual chunk size optimization
"""
import json
import sys
import os

# Add the src directory to Python path
sys.path.append(
    '/Users/shonnli/Non-icloudFile/YouWoAI/Code_V1/YouWoAI-ML-Server/src')


def test_embedding_optimization():
    """Test the embedding optimization with dual chunk sizes"""
    print("🚀 Testing Dual Chunk Size Embedding Optimization")
    print("=" * 70)

    try:
        from utility.note_utils import check_embedding_status, create_and_save_embeddings_both_sizes

        # Test note IDs
        note_ids = [2769, 2771, 2857, 2856, 2272]

        print("📊 Checking current embedding status...")
        status = check_embedding_status(note_ids)

        for note_id, info in status.items():
            print(f"Note {note_id}:")
            print(f"  ✅ Large chunks: {'Yes' if info['has_large'] else 'No'}")
            print(f"  ✅ Small chunks: {'Yes' if info['has_small'] else 'No'}")
            if info['chunk_types']:
                for chunk_type, details in info['chunk_types'].items():
                    print(
                        f"    {chunk_type}: {details['section_count']} sections, size={details['chunk_size']}")

        # Count optimization status
        optimized_count = sum(1 for info in status.values()
                              if info['has_large'] and info['has_small'])

        print(
            f"\n📈 Optimization Status: {optimized_count}/{len(note_ids)} notes fully optimized")

        if optimized_count == len(note_ids):
            print("🎉 All notes are optimized! No re-embedding needed during RAG.")
        else:
            print(
                "⚠️  Some notes need small chunk embeddings. They will be created on first use.")

            # Optionally create missing embeddings
            create_missing = input(
                "\n🔧 Create missing small chunk embeddings now? (y/N): ").lower().strip()

            if create_missing == 'y':
                print("\n🔨 Creating missing embeddings...")
                for note_id, info in status.items():
                    if not (info['has_large'] and info['has_small']):
                        print(f"  Creating embeddings for note {note_id}...")
                        try:
                            create_and_save_embeddings_both_sizes(note_id)
                            print(f"  ✅ Note {note_id} embeddings created")
                        except Exception as e:
                            print(f"  ❌ Note {note_id} failed: {e}")

                print("\n🎉 Optimization complete! Re-run this script to verify.")

        print(f"\n📋 Expected API call reduction:")
        print(
            f"  Before optimization: 1 (query) + {len(note_ids)} (re-embedding) = {1 + len(note_ids)} calls")
        print(f"  After optimization:  1 (query) + 0 (cached) = 1 call")
        print(
            f"  Reduction: {len(note_ids)} fewer embedding API calls per request!")

    except Exception as e:
        print(f"❌ Error: {e}")
        print("Make sure you're running this from the ML server directory with the virtual environment activated.")


if __name__ == "__main__":
    test_embedding_optimization()
