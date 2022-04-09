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

run:
	looper run

test:
	cd tests && python -m pytest -vv --tb=short -ra $(test)

jupyter:
	jupyter lab --ip=0.0.0.0 --port=8080

logs:
	less -R /home/pi/looper/looper.log


remote-create-dir:
	ssh pi "mkdir -p /home/pi/looper"

remote-install-package:
	ssh pi "cd /home/pi/looper &&\
		pip3 install -r requirements.txt &&\
		python3 setup.py develop --user"

remote-install: remote-create-dir push remote-install-package

push:
	rsync -avh --delete --exclude='*.pyc' --exclude='__pycache__' \
		looper Makefile static templates requirements.txt requirements-dev.txt setup.py README.md sfx notebooks \
		pi:/home/pi/looper/

remote-run:
	ssh -t pi "cd /home/pi/looper && python3 -m looper run"

push-and-run: push remote-run

list-looper-ps:
	pgrep -a -f "looper run"

pull-notebooks:
	scp pi:/home/pi/looper/notebooks/*.ipynb notebooks/
