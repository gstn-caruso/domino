GODOT_BIN ?= godot
JAVA_HOME ?=
ANDROID_HOME ?= $(ANDROID_SDK_ROOT)
ACTIONLINT ?= actionlint
VERSION ?= 0.1.1
VERSION_CODE ?= 1
BUILD_DIR ?= builds/$(VERSION)
export GODOT_BIN JAVA_HOME ANDROID_HOME

ifneq ($(strip $(JAVA_HOME)),)
export PATH := $(JAVA_HOME)/bin:$(PATH)
endif

.PHONY: test verify test-exports build run

test:
	"$(GODOT_BIN)" --headless --path . --import
	"$(GODOT_BIN)" --headless --path . --script tests/run.gd
	python3 -m unittest discover -s tests -p 'test_*.py' -v

verify: test
	"$(ACTIONLINT)" .github/workflows/delivery.yml

test-exports:
	RUN_EXPORT_TESTS=1 python3 -m unittest discover -s tests/integration -p 'test_*.py' -v

build:
	python3 scripts/build.py --version "$(VERSION)" --version-code "$(VERSION_CODE)" --output "$(BUILD_DIR)"

run:
	"$(GODOT_BIN)" --headless --path . --import
	"$(GODOT_BIN)" --path .
