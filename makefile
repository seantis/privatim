TIPTAP_DIR ?= src/privatim/static/js/tiptap

install: ensure_uv
	# Check if requirements files exist and compile if needed
	@if [ ! -f requirements.txt ] || [ ! -f test_requirements.txt ]; then \
		echo "One or more requirements files missing, running compile first..."; \
		make compile; \
	fi

	# install requirements
	uv pip install -r requirements.txt -r tests_requirements.txt

	# enable pre-commit
	pre-commit install

	# ensure required folder structure
	mkdir -p ./profiles

	# gather eggs
	rm -rf ./eggs
	scrambler --target eggs

update: ensure_uv
	# update all dependencies
	./requirements/compile.sh -U

	# update the pre-commit hooks
	pre-commit autoupdate

	# apply install step to avoid deviations
	make install

ensure_uv: in_virtual_env
	@if which uv; then true; else pip install uv; fi

	# use latest uv
	uv pip install --upgrade uv

compile: in_virtual_env
	@./requirements/compile.sh

run: in_virtual_env
	pserve --reload development.ini

e2e: in_virtual_env
	pytest tests/ -m "e2e" -vv \
		--browser chromium --browser firefox \
		--retries 3$

# parallel shell execution with & and wait
#
lint: in_virtual_env
	bash ./mypy.sh & \
	flake8 src/ tests/ stubs/ & \
	bash ./bandit.sh & \
	wait

frontend:
	cd $(TIPTAP_DIR) && ./tiptap.sh

in_virtual_env:
	@if python -c 'import sys; (hasattr(sys, "real_prefix") or (hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix)) and sys.exit(1) or sys.exit(0)'; then \
		echo "An active virtual environment is required"; exit 1; \
		else true; fi
