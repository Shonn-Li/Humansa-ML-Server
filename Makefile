VENV_DIR=youwo-ml-venv

.PHONY: format

format:
	black . --exclude $(VENV_DIR)
	isort . --skip $(VENV_DIR)

wyett_init:
	# for Wyett to initialize venv
	conda deactivate
	./youwo-ml-venv/bin/activate