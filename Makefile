SHELL := /bin/bash

.PHONY: doctor setup dev-backend dev-frontend dev run-demo test build contract-check agent-check agent-context e2e preview-reactions backfill-covers dataset-review-pipeline library-source-intake

DATASET_REVIEW_PIPELINE_ARGS ?=
LIBRARY_SOURCE_INTAKE_ARGS ?=

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

run-demo:
	./scripts/run-demo.sh

test:
	./scripts/test.sh

build:
	./scripts/build.sh

contract-check:
	./scripts/contract-check.sh

agent-check:
	./scripts/agent-check.sh

agent-context:
	./scripts/agent-context.sh

e2e:
	./scripts/e2e.sh

preview-reactions:
	./scripts/preview-reactions.sh

backfill-covers:
	./scripts/backfill-covers.sh

dataset-review-pipeline:
	./scripts/dataset-review-pipeline.sh $(DATASET_REVIEW_PIPELINE_ARGS)

library-source-intake:
	./scripts/library-source-intake.sh $(LIBRARY_SOURCE_INTAKE_ARGS)
