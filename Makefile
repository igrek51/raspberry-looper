.PHONY: deploy build run setup test

setup:
	python3 -m venv venv &&\
	. venv/bin/activate &&\
	pip install --upgrade pip setuptools &&\
	pip install -r requirements.txt &&\
	python setup.py develop
	@echo Activate your venv: . venv/bin/activate
