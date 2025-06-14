# YouWoAI ML Server

This is an internal machine learning inference server built with [Quart](https://pgjones.gitlab.io/quart/) and [LlamaIndex](https://github.com/jerryjliu/llama_index). It receives API calls for document-based question answering and is containerized via Docker for deployment (e.g., on AWS EC2).

---

## 🔧 Setup (Local Development)

### 1. Create and activate virtual environment

```bash
python3 -m venv youwo-ml-venv
source youwo-ml-venv/bin/activate
```

### 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the server

```bash
python src/main.py
# By default, the server runs on port 5001.
```

## One liner startup

```bash
python3 -m venv youwo-ml-venv && source youwo-ml-venv/bin/activate &&python -m src.main
```

### 🐳 Running with Docker

```bash
# 1. Build the Docker image
docker build -t youwo-ml-server .
# 2. Run the Docker container
docker run -p 5001:5001 youwo-ml-server
```
