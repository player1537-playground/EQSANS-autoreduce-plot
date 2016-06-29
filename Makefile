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

.PHONY: venv
venv:
ifeq ($(wildcard venv),)
	if [ ! -d $@ ]; then $(PYTHON) -m virtualenv $@; fi
	@echo Run: source $@/bin/activate
	@false
else
ifndef VIRTUAL_ENV
	$(error Run: source $@/bin/activate)
endif
endif

.PHONY: depend
depend: venv
	$(PYTHON) -m pip install -r requirements.txt
	echo $(MANTID_PYTHON_PATH) > $(VIRTUAL_ENV)/lib/python2.7/site-packages/mantid.pth

foo:
	./foo.py
