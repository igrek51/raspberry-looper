.PHONY: deploy build run setup test

setup-latest:
	python3 -m venv venv &&\
	. venv/bin/activate &&\
	pip install --upgrade pip setuptools &&\
	pip install -r requirements.txt &&\
	pip install -r requirements-dev.txt &&\
	python setup.py develop
	@echo Activate your venv:
	@echo . venv/bin/activate

setup-python3.8:
	python3.8 -m venv venv &&\
	. venv/bin/activate &&\
	pip install --upgrade pip setuptools &&\
	pip install -r requirements.txt &&\
	pip install -r requirements-dev.txt &&\
	python setup.py develop
	@echo Activate your venv:
	@echo . venv/bin/activate

setup: setup-python3.8

run:
	looper run

run-nice:
	ionice -c 2 -n 0 nice -n -12 python -m looper run

test:
	cd tests && python -m pytest -vv --tb=short -ra $(test)

jupyter:
	jupyter lab --ip=0.0.0.0 --port=8080

logs:
	less -R /home/pi/looper/looper.log

vnc:
	x11vnc -forever -display :0


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

remote-kill:
	ssh -t pi "screen -S looper -X at '#' stuff '^C'"

push-and-run: push remote-run

list-looper-ps:
	pgrep -a -f "looper run"

screen-run:
	screen -S looper bash -c "python3 -m looper run |& tee /home/pi/looper/looper.log"

screen-kill:
	screen -S looper -X at '#' stuff '^C'

pull-notebooks:
	scp pi:/home/pi/looper/notebooks/*.ipynb notebooks/


docker-build:
	DOCKER_BUILDKIT=1 docker build -t igrek52/raspberry-looper:latest -f Dockerfile .

docker-run: docker-build
	docker run -it --rm \
		-p 8000:8000 \
		--name raspberry-looper \
		--device /dev/snd \
		--privileged=true \
		igrek52/raspberry-looper:latest

docker-push:
	docker login -u igrek52
	docker push igrek52/raspberry-looper:latest
