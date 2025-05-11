VENV_DIR=youwo-ml-venv

.PHONY: format

format:
	black . --exclude $(VENV_DIR)
	isort . --skip $(VENV_DIR)
