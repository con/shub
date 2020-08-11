FROM python:3.7
COPY requirements.txt serve.py /usr/src/
RUN python3 -m pip install --upgrade pip && \
    python3 -m pip install -r /usr/src/requirements.txt
CMD ["python", "/usr/src/serve.py"]
