GDAL_VERSION := $(shell gdal-config --version)

.PHONY: all
all: $(ALL_TARGETS) test

.PHONY: test
test: packages codestyle
	@echo "Running tests...."
	@. venv/bin/activate; pytest -v tests
	@echo "Done."

test_%: packages
	@. venv/bin/activate; tests/$@.py

.PHONY: codestyle
codestyle: packages
	@. venv/bin/activate; which flake8 >/dev/null || (echo "flake8 checker not available" && exit 1)
	@echo "Checking python code style (PEP8)"
	@. venv/bin/activate; flake8 navigator tests
	@echo "Done."

.PHONY: clean
clean:
	@echo "Cleaning up python cache..."
	@find . -type d -name __pycache__ | xargs rm -rf
	@echo "Done."

.PHONY: distclean
distclean: clean
	@echo "Removing virtual environment..."
	@which python | grep venv >/dev/null 2>/dev/null && echo "Deactivate your virtual environment first" && exit 1 || echo "Virtual environment not active" 
	@rm -rf venv
	@echo "Done."

.PHONY: packages
packages: venv/updated

venv/bin/activate:
	@echo "Setting up virtual environment..."
	@if [ ! -e /usr/include/gdal ]; then echo "GDAL develeopment files are required"; exit 1; fi
	@(which python3.8 >/dev/null && python3.8 -mvenv venv) || \
	   (which python3.7 >/dev/null && python3.7 -mvenv venv)
	@cp /usr/include/gdal/* venv/include/
	@echo "Done."

venv/updated: venv/bin/activate requirements.txt
	@echo "Installing packages ..." 
	@echo "GDAL: ${GDAL_VERSION}"
	@. venv/bin/activate \
		&& pip install wheel \
		&& pip install ipython \
		&& pip install -r requirements.txt \
	    && pip install gdal==${GDAL_VERSION}
	@touch venv/updated
	@echo "Done."

.PHONY: create_db
create_db:
	@which psql >/dev/null || (echo "Requires psql command"; exit 1)
	@. ./.env; test ! -z $$DATABASE_USER || (echo "Requires database user: set DATABASE_USER"; exit 1)
	@. ./.env; test ! -z $$DATABASE_PASS || (echo "Requires database password: set DATABASE_PASS"; exit 1)
	@. ./.env; test ! -z $$DATABASE_NAME || (echo "Requires database name: set DATABASE_NAME"; exit 1)
	@. ./.env; sudo -E -u postgres psql -c "CREATE ROLE $$DATABASE_USER WITH LOGIN ENCRYPTED PASSWORD '$$DATABASE_PASS';"
	@. ./.env; sudo -E -u postgres psql -c "CREATE DATABASE $$DATABASE_NAME WITH OWNER '$$DATABASE_USER';"
	@. ./.env; sudo -E -u postgres sh -c "echo '\\\c $$DATABASE_NAME\nCREATE EXTENSION pg_trgm;' | psql"

.PHONY: upgrade_db
upgrade_db: packages
	@echo "Upgrading database..."
	@. venv/bin/activate; alembic upgrade head
	@echo "Done."

.PHONY: create_db_upgrade
create_db_upgrade: upgrade_db
	@echo "Creating new database migration"
	@. venv/bin/activate; alembic revision --autogenerate
	@. venv/bin/activate; alembic heads | head -n 1 | awk '{ print "version = \""$$1"\""}' > cointrader/database/_version.py

.PHONY: drop_db
drop_db:
	@which psql >/dev/null || (echo "Requires psql command"; exit 1)
	@. ./.env; test ! -z $$DATABASE_USER || (echo "Requires database user: set DATABASE_USER"; exit 1)
	@. ./.env; test ! -z $$DATABASE_NAME || (echo "Requires database name: set DATABASE_NAME"; exit 1)
	@. ./.env; sudo -E -u postgres psql -c "DROP DATABASE IF EXISTS $$DATABASE_NAME;"
	@. ./.env; sudo -E -u postgres psql -c "DROP ROLE IF EXISTS $$DATABASE_USER;"
