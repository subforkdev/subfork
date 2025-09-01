# =============================================================================
# Project: Subfork Python API
#
# Usage:
#   make           - Builds targets
#   make clean     - Removes all build artifacts
#   make build     - Builds the requirements for Linux
#   make install   - Installs the build artifacts using distman
#   make start	   - Starts the systemd service
#
# Requirements:
#   - Installs and dists python requirements
#   - Starts a systemd service for the project
# =============================================================================

# Define the installation command
PROJECT := subfork
BUILD_DIR := $(CURDIR)/build
BUILD_CMD := pip install -r requirements.txt -t $(BUILD_DIR)
DEPLOY_ROOT ?= /etc/${PROJECT}

# envstack command uses ./env for ENVPATH
ENVSTACK_CMD := ENVPATH=$(CURDIR)/env \
                PATH=$(BUILD_DIR)/bin:$$PATH \
                PYTHONPATH=$(BUILD_DIR):$$PYTHONPATH \
                envstack ${PROJECT}

# Remove __pycache__ directories from the build directory
RM_PYCACHE_CMD := find $(BUILD_DIR) -type d -name '__pycache__' -exec rm -rf {} +

# Target to build for Linux
build: clean
	$(BUILD_CMD)
	$(RM_PYCACHE_CMD)

# Clean target to remove the build directory
clean:
	rm -rf build

# Install target to install the builds using distman
dryrun:
	$(ENVSTACK_CMD) -- dist --force --dryrun

# Start the systemd service
start: install
	@echo "Starting ${PROJECT} service..."
	$(ENVSTACK_CMD) -- ln -sfn {DEPLOY_ROOT}/services/${PROJECT}/${PROJECT}.service \
		/etc/systemd/system/${PROJECT}.service
	sudo systemctl enable ${PROJECT} || true
	systemctl daemon-reload || true
	sudo systemctl restart ${PROJECT} || sudo systemctl start ${PROJECT}

# Run the dev server
run:
	@command -v envstack >/dev/null 2>&1 || { echo >&2 "envstack not installed, run make install."; exit 1; }
	$(ENVSTACK_CMD) -- subfork run

# Install target to install the builds using distman
install: build
	@echo "Installing ${PROJECT} using distman..."
	$(ENVSTACK_CMD) -- dist --yes
	$(MAKE) start

# Phony targets
.PHONY: build dryrun install clean start
