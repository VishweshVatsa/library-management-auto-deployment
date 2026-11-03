# Containerized Library Management System with Automated CI/CD

A Flask + SQLite library app (books, members, issue/return) packaged in Docker
and deployed automatically by a GitHub Actions pipeline.

## Architecture

    Developer --git push--> GitHub --> GitHub Actions
                                          1. test   (pytest)
                                          2. build  (Docker image) -> push to Docker Hub
                                          3. deploy (SSH into VM: pull image, restart container)
                                                         |
                                                   Cloud VM (AWS EC2 / any Linux)
                                                   Docker container on port 80

## 1. Run locally (no Docker)

    python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
    pip install -r requirements.txt
    python -m pytest -v          # run the tests
    python -m app.main           # open http://localhost:5000

## 2. Run with Docker

    docker compose up --build    # open http://localhost

## 3. Set up the pipeline

1. Create a GitHub repo and push this folder to the `main` branch.
2. Create a Docker Hub account and an access token (Account settings > Security).
3. Launch a free-tier Ubuntu VM and install Docker: `curl -fsSL https://get.docker.com | sh`
   Open port 80 in the VM's security group.
4. In GitHub: Settings > Secrets and variables > Actions > add these secrets:

   | Secret | Value |
   |---|---|
   | DOCKERHUB_USERNAME | your Docker Hub username |
   | DOCKERHUB_TOKEN | the Docker Hub access token |
   | SSH_HOST | public IP of the VM |
   | SSH_USER | e.g. `ubuntu` |
   | SSH_KEY | the full private key (.pem) text |

5. Push a change to `main`. Watch Actions: test -> build-and-push -> deploy.
6. Visit `http://<VM-IP>`.

No VM? Delete the `deploy` job and demo with `docker run -p 5000:5000 <user>/library-management`.

## Demo script (viva)

1. Show the app running; add a book and a member; issue and return a book.
2. Change a line of text in a template, commit, push.
3. Show the Actions run going green, then refresh the site to show the change live.
4. Break a test on purpose, push, and show the pipeline stopping before deploy.

## Likely viva questions

- **What is CI/CD?** CI builds and tests every commit automatically; CD ships passing builds to the server.
- **Why Docker?** The app runs identically on every machine: same Python, same libraries.
- **Why does deploy depend on test?** Broken code never reaches production.
- **Why a volume at /data?** Containers are disposable; the volume keeps the database when the container is replaced.
- **Why gunicorn, not `flask run`?** The Flask dev server is not meant for production.
- **Why tag images with the commit SHA?** Gives a traceable version and easy rollback.
