#!/usr/bin/env python3
"""
Export embeddings from production database without tsvector
Maps production note IDs to test note IDs
"""

import psycopg2
import json
from datetime import datetime

# Production database
PROD_DB = {
    'host': 'localhost',
    'port': 5432,
    'database': 'test4',
    'user': 'postgres',
    'password': '031203'
}

# Note ID mapping: production -> test
NOTE_ID_MAP = {
    7285: 10001,  # 2311.18703v5.pdf
    7284: 10002,  # 2505.18499v2.pdf
    7283: 10003,  # 2505.06319v1.pdf
    7289: 10004,  # Startup Ideas You Can Now Build With AI
    7288: 10005,  # How Zepto Became India's Fastest Growing Startup
    7287: 10006,  # How Replit Went From $10M to $100M ARR
    7286: 10007,  # Andrew Ng: Building Faster with AI
    7257: 10008,  # 欢迎来到由我AI.docx
    7253: 10009,  # Product demo
}

def connect_to_db(config):
    """Connect to PostgreSQL database"""
    try:
        conn = psycopg2.connect(**config)
        return conn
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return None

def export_embeddings(conn):
    """Export embeddings for specified notes"""
    cur = conn.cursor()
    
    # Get all embeddings for our notes
    prod_note_ids = list(NOTE_ID_MAP.keys())
    
    cur.execute("""
        SELECT 
            type_id,
            type,
            section_id,
            embedding::text,
            chunk_text,
            source,
            url,
            metadata,
            last_updated
        FROM embedding_v1
        WHERE type = 'note' 
        AND type_id = ANY(%s)
        ORDER BY type_id, section_id
    """, (prod_note_ids,))
    
    embeddings = []
    for row in cur.fetchall():
        # Map production ID to test ID
        test_note_id = NOTE_ID_MAP.get(row[0])
        if test_note_id:
            embeddings.append({
                'type_id': test_note_id,
                'type': row[1],
                'section_id': row[2],
                'embedding': row[3],
                'chunk_text': row[4],
                'source': row[5],
                'url': row[6],
                'metadata': row[7],
                'last_updated': row[8].isoformat() if row[8] else None
            })
    
    return embeddings

def generate_sql(embeddings):
    """Generate SQL INSERT statements for embeddings"""
    sql_lines = []
    
    # Header
    sql_lines.append("-- Embeddings for test data (simplified without tsvector)")
    sql_lines.append(f"-- Exported at: {datetime.now().isoformat()}")
    sql_lines.append(f"-- Total embeddings: {len(embeddings)}")
    sql_lines.append("")
    
    # Insert in batches to avoid SQL length limits
    batch_size = 5
    
    for i in range(0, len(embeddings), batch_size):
        batch = embeddings[i:i+batch_size]
        
        sql_lines.append("INSERT INTO embedding_v1 (")
        sql_lines.append("  type_id, type, section_id, embedding, chunk_text,")
        sql_lines.append("  source, url, metadata, last_updated")
        sql_lines.append(")")
        sql_lines.append("VALUES")
        
        values = []
        for emb in batch:
            # Escape single quotes properly
            chunk_text = emb['chunk_text'].replace("'", "''") if emb['chunk_text'] else ''
            metadata_json = json.dumps(emb['metadata']).replace("'", "''") if emb['metadata'] else '{}'
            url = emb['url'].replace("'", "''") if emb['url'] else None
            
            # Format values
            embedding_val = f"'{emb['embedding']}'::vector" if emb['embedding'] else 'NULL'
            url_val = f"'{url}'" if url else 'NULL'
            
            values.append(
                f"  ({emb['type_id']}, '{emb['type']}'::varchar(50), {emb['section_id']}, "
                f"{embedding_val}, E'{chunk_text}'::text, "
                f"'{emb['source']}'::varchar(50), {url_val}, '{metadata_json}'::jsonb, "
                f"NOW())"
            )
        
        sql_lines.append(",\n".join(values))
        sql_lines.append("ON CONFLICT (type_id, type, section_id) DO NOTHING;")
        sql_lines.append("")
    
    # Add verification query
    sql_lines.append("-- Verify embeddings loaded")
    sql_lines.append("SELECT ")
    sql_lines.append("  COUNT(*) as total_embeddings,")
    sql_lines.append("  COUNT(DISTINCT type_id) as unique_notes,")
    sql_lines.append("  array_agg(DISTINCT type_id ORDER BY type_id) as note_ids")
    sql_lines.append("FROM embedding_v1")
    sql_lines.append("WHERE type = 'note' AND type_id >= 10001;")
    
    return '\n'.join(sql_lines)

def main():
    print("Exporting embeddings from production database (simplified)...")
    
    # Connect to production
    conn = connect_to_db(PROD_DB)
    if not conn:
        return
    
    try:
        # Export embeddings
        embeddings = export_embeddings(conn)
        print(f"Exported {len(embeddings)} embeddings")
        
        # Count by note
        note_counts = {}
        for emb in embeddings:
            note_id = emb['type_id']
            note_counts[note_id] = note_counts.get(note_id, 0) + 1
        
        print("\nEmbeddings per note:")
        for note_id in sorted(note_counts.keys()):
            prod_id = [k for k, v in NOTE_ID_MAP.items() if v == note_id][0]
            print(f"  Note {note_id} (was {prod_id}): {note_counts[note_id]} embeddings")
        
        # Generate SQL
        sql = generate_sql(embeddings)
        
        # Save to file
        output_path = '../sql/04_embeddings_simple.sql'
        with open(output_path, 'w') as f:
            f.write(sql)
        
        print(f"\nSQL saved to: {output_path}")
        print(f"File size: {len(sql) / 1024:.2f} KB")
        
    finally:
        conn.close()

if __name__ == "__main__":
    main()