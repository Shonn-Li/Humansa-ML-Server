Validation steps:

- For YouWoAI-ML-Server related changes, when finished applying changes, use "lsof -ti tcp:5001 | xargs -r kill -9 && \
  source YouWoAI-ML-Server/youwo-ml-venv/bin/activate && \
  python YouWoAI-ML-Server/src/main.py"
  to restart the server and ensure the changes are applied, and then test the relevant endpoints changes as well as check log output.

## 3. youwoai‑ml‑server (Port 5001)

- Python service in a virtual environment:

  ```bash
  # Restart the ML server on port 5001
  lsof -ti tcp:5001 | xargs -r kill -9 && \
  source YouWoAI-ML-Server/youwo-ml-venv/bin/activate && \
  python YouWoAI-ML-Server/src/main.py
  ```

- Dependencies in `requirements.txt`:

  ```bash
  source YouWoAI-ML-Server/youwo-ml-venv/bin/activate
  pip install -r YouWoAI-ML-Server/requirements.txt
  ```

### Chat Endpoint

- The primary `/chat` endpoint implements the modular flow (see **YouWoAI modular flow diagram**).
- If you update logic here, also update the corresponding diagram in `documentation/`.

---

## 5. documentation

- All guides, diagrams, and flowcharts live here in Markdown.
- Use **Mermaid** for flow diagrams and graph diagrams:

  - Mermaid nodes do **not** support double quotes (`"`) inside descriptions.
  - Use single quotes (`'`) inside a node description instead.
  - If you need brackets or complex text, wrap the entire node in double quotes, e.g.:

    ```mermaid
    flowchart TD
      NODE["functioncall('username1')"] --> NEXT["...next step..."]
    ```

- Update or add docs whenever you introduce or modify features, endpoints, or infrastructure.
- Reference the **YouWoAI modular flow diagram** and ensure it matches code behavior.
