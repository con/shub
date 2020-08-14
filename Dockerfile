# Sanic LTS (18.12) and Alpine
FROM sanicframework/sanic:LTS

WORKDIR /opt
COPY . .

RUN pip3 install -r /opt/requirements.txt
CMD ["python", "serve.py"]
