-- Install pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create a new table for vector search
CREATE TABLE IF NOT EXISTS note_embeddings_vector (
    id SERIAL PRIMARY KEY,
    note_id INTEGER NOT NULL REFERENCES note_v1(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    chunk_text TEXT,
    embedding vector(1536),  -- Adjust dimension based on your model
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(note_id, chunk_index)
);

-- Create an HNSW index for fast similarity search
CREATE INDEX IF NOT EXISTS note_embeddings_vector_hnsw_idx 
ON note_embeddings_vector 
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Create index on note_id for filtering
CREATE INDEX IF NOT EXISTS idx_note_embeddings_vector_note_id 
ON note_embeddings_vector(note_id);

-- Function to search similar embeddings
CREATE OR REPLACE FUNCTION search_similar_notes(
    query_embedding vector,
    note_id_list INTEGER[],
    limit_count INTEGER DEFAULT 5
)
RETURNS TABLE(
    note_id INTEGER,
    chunk_index INTEGER,
    similarity FLOAT,
    chunk_text TEXT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        nev.note_id,
        nev.chunk_index,
        1 - (nev.embedding <=> query_embedding) as similarity,
        nev.chunk_text
    FROM note_embeddings_vector nev
    WHERE nev.note_id = ANY(note_id_list)
    ORDER BY nev.embedding <=> query_embedding
    LIMIT limit_count;
END;
$$;
