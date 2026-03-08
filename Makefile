SHELL := /bin/bash

.PHONY: doctor setup dev-backend dev-frontend dev test build

doctor:
	./scripts/doctor.sh

setup:
	./scripts/setup.sh

dev-backend:
	./scripts/dev-backend.sh

dev-frontend:
	./scripts/dev-frontend.sh

dev:
	./scripts/dev.sh

test:
	./scripts/test.sh

build:
	./scripts/build.sh
