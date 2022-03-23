.PHONY: deploy build run setup test

setup:
	python3 -m venv venv &&\
	. venv/bin/activate &&\
	pip install --upgrade pip setuptools &&\
	pip install -r requirements.txt &&\
	python setup.py develop --user
	@echo Activate your venv:
	@echo . venv/bin/activate

push-first:
	ssh pi "mkdir -p /home/pi/looper"
	scp -r looper Makefile requirements.txt setup.py pi:/home/pi/looper/
	ssh pi "cd /home/pi/looper &&\
		pip install -r requirements.txt &&\
		python setup.py develop --user"

push:
	scp -r looper Makefile pi:/home/pi/looper/

run:
	looper wire
