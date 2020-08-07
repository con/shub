FROM python:3.7
RUN python3 -m pip install --upgrade pip && \
    python3 -m pip install requests sanic sanic-cors
COPY serve.py /usr/src
CMD ["python", "/usr/src/serve.py"]
