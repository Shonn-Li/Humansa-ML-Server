# YouWoAI Test Environment

This directory contains a complete, isolated test environment for YouWoAI with a PostgreSQL database running on port 5454.

## Features

- **Isolated PostgreSQL instance** with pgvector extension on port 5454
- **Complete test dataset** including:
  - 1 test user with full configuration
  - 2 folders (June-ML, Startup)
  - 9 notes with various types (YouTube videos, PDFs, audio, documents)
  - 190 real embeddings exported from production
  - 9 rich conversations with proper titles demonstrating:
    - Technical Q&A on research papers
    - Startup and business discussions
    - Multi-language support (Chinese and English)
    - Various conversation depths (4-6 messages each)
- **All production API keys** configured in `.env.test`
- **One-command setup** with automatic verification

## Quick Start

```bash
# 1. Run the setup script
./scripts/setup.sh

# 2. The script will:
#    - Export embeddings from production (if needed)
#    - Start PostgreSQL on port 5454
#    - Create all tables
#    - Load test data
#    - Verify everything works

# 3. Connect to the test database
PGPASSWORD=12931 psql -h localhost -p 5454 -U postgres -d youwoai_test
```

## Configuration

### Database Connection
- **Host**: localhost
- **Port**: 5454 (different from production 5432)
- **Database**: youwoai_test
- **Username**: postgres
- **Password**: 12931

### Environment Variables
All production API keys are preserved in `.env.test`, only the database port is changed to 5454.

## Test Data

For detailed information about each note's content and testing scenarios, see [TEST_DATA_GUIDE.md](./TEST_DATA_GUIDE.md).

### Users (IDs 10001-10003)
- `test_Shonn Li` - Main test user with all content
- `test_investor` - Secondary user
- `test_admin` - Admin user

### Folders (IDs 10001-10002)
- **June-ML**: 3 ML research papers
- **Startup**: 4 YouTube videos about startups

### Notes (IDs 10001-10009)
- 3 ML papers (PDFs with summaries)
- 4 YouTube videos (with transcripts)
- 1 document (YouWoAI intro)
- 1 audio note (Product demo with Chinese transcript)

### Embeddings
- 190 embeddings total
- All notes have complete embeddings
- Supports vector similarity search

### Conversations
- 9 conversations covering all test notes
- Rich Q&A demonstrating system capabilities
- Proper titles for easy navigation
- Mix of technical and casual discussions

## Useful Commands

```bash
# Start the test database
docker-compose up -d

# View logs
docker-compose logs -f postgres-test

# Connect to database
PGPASSWORD=12931 psql -h localhost -p 5454 -U postgres -d youwoai_test

# Verify setup
python3 scripts/verify_setup.py

# Stop database
docker-compose down

# Clean up everything (removes all data)
docker-compose down -v
```

## Configuring Applications

### Backend Server
Update your backend `.env`:
```bash
DB_PORT=5454  # Change from 5432
DB_ACTIVE_DATABASE=youwoai_test
```

### ML Server
Update your ML server `.env`:
```bash
DB_PORT=5454  # Change from 5432
DB_ACTIVE_DATABASE=youwoai_test
```

## Troubleshooting

### Port Already in Use
If port 5454 is already in use, edit `docker-compose.yml` and change the port mapping.

### Python Dependencies
The setup script requires `psycopg2-binary`. Install with:
```bash
pip3 install psycopg2-binary
```

### Docker Not Running
Make sure Docker Desktop is running before running the setup script.

### Embeddings Export Failed
The script will try to use the ML server's virtual environment. If it fails, manually activate a Python environment with psycopg2 and run:
```bash
cd scripts
python export_embeddings.py
```

## Architecture

```
test_environment/
├── docker-compose.yml      # PostgreSQL container configuration
├── .env.test              # Test environment variables
├── sql/
│   ├── 01_extensions.sql  # pgvector and pg_trgm
│   ├── 02_create_tables.sql # All table schemas
│   ├── 03_test_data.sql   # Test users, folders, notes
│   └── 04_embeddings.sql  # 190 embeddings (4.5MB)
├── scripts/
│   ├── setup.sh           # Main setup script
│   ├── export_embeddings.py # Export from production
│   └── verify_setup.py    # Verification script
├── README.md              # This file
└── TEST_DATA_GUIDE.md     # Detailed guide to test data content
```