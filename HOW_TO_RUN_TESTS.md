# How to Run the Agent Tests

## Prerequisites

1. Make sure the test database is running:
```bash
cd /Users/shonnli/Non-icloudFile/YouWoAI/Code_V1/test_environment
docker-compose up -d
```

2. Make sure the ML server is running with test configuration:
```bash
cd /Users/shonnli/Non-icloudFile/YouWoAI/Code_V1/YouWoAI-ML-Server
source youwo-ml-venv/bin/activate
python src/main.py
```

## Running the Tests

### Option 1: Clean Output Test (Recommended)
This shows human-readable results with query → agents → response

```bash
cd /Users/shonnli/Non-icloudFile/YouWoAI/Code_V1/YouWoAI-ML-Server
source youwo-ml-venv/bin/activate
python test_clean_output.py
```

### Option 2: Final Status Test
This shows a quick summary of what's working and what's not

```bash
cd /Users/shonnli/Non-icloudFile/YouWoAI/Code_V1/YouWoAI-ML-Server
source youwo-ml-venv/bin/activate
python test_final_status.py
```

### Option 3: Full Test Suite
This runs comprehensive tests but output is more technical

```bash
cd /Users/shonnli/Non-icloudFile/YouWoAI/Code_V1/YouWoAI-ML-Server
source youwo-ml-venv/bin/activate
python tests/test_agents_real_environment.py
```

## Quick One-Liner Commands

If you want to run everything in one command from anywhere:

### Run Clean Test:
```bash
cd /Users/shonnli/Non-icloudFile/YouWoAI/Code_V1/YouWoAI-ML-Server && source youwo-ml-venv/bin/activate && python test_clean_output.py
```

### Run Status Test:
```bash
cd /Users/shonnli/Non-icloudFile/YouWoAI/Code_V1/YouWoAI-ML-Server && source youwo-ml-venv/bin/activate && python test_final_status.py
```

## Understanding the Output

### Clean Output Test Example:
```
================================================================================
TEST: Web Search
QUERY: What are the latest AI developments today?
--------------------------------------------------------------------------------
AGENTS: router → web_search → response
STATUS: SUCCESS

RESPONSE:
Here are some of the latest AI developments as of July 2025...
```

### Status Test Example:
```
Testing: RAG - Note Search
Query: What information is in my PARL paper note?
Result: ✅
Agents: router → rag → response
```

## Troubleshooting

### If ML Server is Not Running:
```bash
# Check if it's running
lsof -i:5001

# If not, start it:
cd /Users/shonnli/Non-icloudFile/YouWoAI/Code_V1/YouWoAI-ML-Server
source youwo-ml-venv/bin/activate
python src/main.py
```

### If Test Database is Not Running:
```bash
# Check if it's running
docker ps | grep youwoai_test_db

# If not, start it:
cd /Users/shonnli/Non-icloudFile/YouWoAI/Code_V1/test_environment
docker-compose up -d
```

### To Switch Back to Production:
```bash
cd /Users/shonnli/Non-icloudFile/YouWoAI/Code_V1/YouWoAI-ML-Server
source youwo-ml-venv/bin/activate
python tests/setup_test_environment.py restore
```

## Test Results Location

- Test results are saved as JSON files with timestamps
- Look for files like `test_results_*.json` in the ML server directory
- Logs are in `ml_server_test.log`