.PHONY: deploy build run setup test

setup:
	python3 -m venv venv &&\
	. venv/bin/activate &&\
	pip install --upgrade pip setuptools &&\
	pip install -r requirements.txt &&\
	pip install -r requirements-dev.txt &&\
	python setup.py develop --user
	@echo Activate your venv:
	@echo . venv/bin/activate

push-first:
	ssh pi "mkdir -p /home/pi/looper"
	scp -r \
		looper Makefile requirements.txt requirements-dev.txt setup.py README.md notebooks static templates \
		pi:/home/pi/looper/
	ssh pi "cd /home/pi/looper &&\
		pip install -r requirements.txt &&\
		python setup.py develop --user"

push:
	scp -r looper Makefile static templates pi:/home/pi/looper/

run:
	looper run

jupyter:
	jupyter lab --ip=0.0.0.0 --port=8080

pull-notebooks:
	scp pi:/home/pi/looper/notebooks/*.ipynb notebooks/

test:
	cd tests && python -m pytest -vv --tb=short -ra $(test)
