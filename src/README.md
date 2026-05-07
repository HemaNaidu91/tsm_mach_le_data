# Build and start the application

This is a quick guide on how to build and start the application

Notes:
- About environments:
  - All virtual environments should be named ```.venv```
  - The config files should be named ```.env```
  - The .env-files will be added to the repo. This is usually not reccomended. But because this is only a school project with public data, there is no real security risk. Additionally, it makes the hand-in of the project easier.
- About backend:
  - The backend uses a simplified structure due to its limited size

## For Poduction - with docker

1. Adjust the ```/backend/.evv``` file:
      1. ```POSTGRES_HOST=db```
      2. ```MODEL_SERVICE_URL=http://model-service:8001```
2. Adjust the ```/frontend/.evv``` file:
      1. ```API_URL=http://backend:8001```
3. Open a shell or bash:
   1. Navigate to the ./src directory
   2. run to build and boot:
      1. shell: ```docker compose -f docker-compose.prod.yml up --build```
      2. bash: ```docker compose -f docker-compose.prod.yml up --build```

## For Development - without docker

1. Install and launch PostgreSQL Server
   1. Installation guide: <a href='https://www.postgresql.org/download/'>PostgreSQL Downloads</a><br>Important: Create a user with the following credentials (or change the connection config in ./src/backend/.env if you must):
      1. username: postgres
      2. password: postgres
   2. If not automatically launched, run:
      1. shell: ```net start postgresql-x64-18```
      2. bash:  ```sudo systemctl start postgresql```
   3. Create a database named <i>cinematch</i>
   4. Install the postgres .dump file (see: <a href='https://www.bytebase.com/reference/postgres/how-to/how-to-install-pgdump-on-mac-ubuntu-centos-windows/'>How to install pg_dump on your Mac, Ubuntu, CentOS, Windows</a>)
   5. Adjust the ```/backend/.evv``` file:
      1. For local use: ```POSTGRES_HOST=localhost```
      2. (For docker use: ```POSTGRES_HOST=db```)
   
2. Create and install the local virtual environments as ```.venv```:
   1. Setup as:
      1. ```.src/backend/.venv/```
      2. ```.src/frontend/.venv/```
      3. ```.src/model-service/.venv/```
   2. Activate and install the concerning reqruirements with uv

3. Boot the services:
   1. Backend: ```run_dev_server.py```
   2. Frontend: ```streamlit run main.py```
   3. Model Service: ```model-service.py```

4. FsatAPI Docu available at:
   1. Backend <a href="localhost:8000/docs">localhost:8000/docs</a> or <a href="127.0.0.1:8000/docs">127.0.0.1:8000/docs</a>.
   2. Model Service <a href="localhost:8001/docs">localhost:8000/docs</a> or <a href="127.0.0.1:8001/docs">127.0.0.1:8000/docs</a>.


## For Deployment - with Docker
tbd


## Shutdown PostgresQL

- shell shutdown postgreSQL: ```net stop postgresql-x64-18```
- bash shutdown postgreSQL: ```sudo systemctl stop postgresql```