MAKEFLAGS += --warn-undefined-variables
SHELL := bash
.SHELLFLAGS := -eu -o pipefail -c
.DEFAULT_GOAL := all
.DELETE_ON_ERROR:
.SUFFIXES:

ifndef MANTID_PYTHON_PATH
MANTID_PYTHON_PATH := /opt/Mantid/bin
endif

ifndef PYTHON
PYTHON := python
endif

.PHONY: depend
depend:
	test -n "$(VIRTUAL_ENV)" # $$VIRTUAL_ENV (Fix: source venv/bin/activate)
	$(PYTHON) -m pip install -r requirements.txt
	echo $(MANTID_PYTHON_PATH) > $(VIRTUAL_ENV)/lib/python2.7/site-packages/mantid.pth
