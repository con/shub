# Singularity-Hub.org (shub) read-only implementation

This repository is based on https://github.com/dandi/redirector
which is taken as the basis to establish desired functionality.

Notes below are just for references and some code around which points
to DANDI infrstructure components is not relevant, and will be cleaned up
later.

## Current install process on instance

#### install pre-requisites

```
apt-get update
apt-get install -y git python3.7 nginx vim fail2ban python3.7-dev python3-pip
```

#### Setup nginx
```
vi /etc/nginx/sites-enabled/girder.dandiarchive.org
```
edit nginx site file
```
server {
       listen 80;
       server_name    dandiarchive.org;
       location / {
          proxy_pass http://localhost:8080/;
          proxy_set_header Host $host;
          proxy_set_header X-Real-IP $remote_addr;
          proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
      }
}
```

#### restart nginx
```
service nginx restart
service nginx status
```

#### setup lets encrypt
```
add-apt-repository -y ppa:certbot/certbot
apt-get update
apt-get install -y certbot python-certbot-nginx
certbot --nginx
```

#### make a local pip upgrade
```
python3.7 -m pip install --upgrade pip
```

#### clone repo and run
```
git clone https://github.com/dandi/redirector.git
cd redirector
pip3.7 install -r requirements.txt
nohup python3.7 serve.py &
```

## Development

This repo uses pre-commit for styling and syntax checks. To use in your Python
+ git environment, do:

```
pip install pre-commit
pre-commit install
```

After this, it will run the pre-commit checks on every git commit, make any
adjustments as necessary, and request that you git commit again.
