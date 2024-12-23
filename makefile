TIPTAP_DIR ?= src/privatim/static/js/tiptap

install: ensure_uv
	# install requirements
	uv pip install -e '.[test,mypy,dev]' --config-settings editable_mode=compat

	# enable pre-commit
	pre-commit install

	# ensure required folder structure
	mkdir -p ./profiles

	# gather eggs
	rm -rf ./eggs
	scrambler --target eggs

update: ensure_uv
	# update all dependencies
	uv pip compile setup.cfg -U --all-extras | uv pip install -U -r /dev/stdin

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

frontend:
	cd $(TIPTAP_DIR) && ./tiptap.sh

in_virtual_env:
	@if python -c 'import sys; (hasattr(sys, "real_prefix") or (hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix)) and sys.exit(1) or sys.exit(0)'; then \
		echo "An active virtual environment is required"; exit 1; \
		else true; fi
