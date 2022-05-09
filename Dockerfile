FROM python:3.8-slim-buster

RUN apt-get update -y && apt-get install -y \
    python3-pyaudio \
    portaudio19-dev \
    libatlas-base-dev \
    ffmpeg \
    gcc

WORKDIR /src/

COPY setup.py requirements.txt /src/
RUN pip install -r /src/requirements.txt

COPY sfx/. /src/sfx/
COPY static/. /src/static/
COPY templates/. /src/templates/
COPY looper/. /src/looper/

RUN python setup.py develop

CMD python -u -m looper run
EXPOSE 8000
