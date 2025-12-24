# github-app-python

- [Create Github App](https://docs.github.com/en/apps/creating-github-apps)
- [Smee start channel](https://smee.io/8pLy0kP1cyDzDT)
- [Docker.py](https://github.com/docker/docker-py)
- [Smee.io](https://smee.io/)

## Commands

### Python

```sh
pipenv shell
pipenv lock
pipenv sync
pip freeze
pip install --no-cache-dir -r requirements.txt
pip freeze > requirements.txt
pipenv --venv
```

## Quick Start

1. Create a new Smee channel
  - Open https://smee.io in your browser.​
  - Click Start a new channel.
  - Copy the Webhook Proxy URL at the top (for example, https://smee.io/abc123...).
  - This URL will be used as the webhook URL for your GitHub App so Smee can receive events.
  - Update `.envrc` with this channel
2. Register a GitHub App using the Smee URL
   - On GitHub, go to: `Settings → Developer settings → GitHub Apps → New GitHub App`.
   - Fill in the required fields (name, homepage URL, etc.)
   - Webhook URL -> our smee.io url `https://smee.io/abc123....`
   - Webhook secret -> `uuid`
3. Create a private key
   - Flatten ssh key with `cat <KEY_PATH> | base64`
4. Install Github App in the Github location of you choice
5. Build and run
   - `mk docker-compose-up`

## Resources

- [Fastapi](https://github.com/fastapi/fastapi)
- [Fastapi template](https://github.com/fastapi/full-stack-fastapi-template)
- [Fastapi Github](https://pypi.org/project/fastapi-githubapp/)
- [Probot: smee](https://github.com/probot/smee-client)
- [Fastapi: medium](https://hasansajedi.medium.com/fastapi-and-github-actions-67d86c1e6c5f)
