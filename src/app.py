import os
import base64
from fastapi import FastAPI
from githubapp import GitHubApp
# GitHubAppMiddleware, GitHubAppEventHandler

app = FastAPI()

# Decode the base64-encoded private key
private_key_base64 = os.getenv("GITHUB_APP_PRIVATE_KEY")
private_key = base64.b64decode(private_key_base64).decode('utf-8')

github_app = GitHubApp(
    app,
    github_app_id=int(os.getenv("GITHUB_APP_ID")),
    github_app_key=private_key,
    github_app_secret=os.getenv("GITHUB_WEBHOOK_SECRET").encode()
    github_app_route="/webhooks/github",
)

@app.get("/status")
def index():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)), log_level="info", reload=True)

# TODO: Integrate GitHubApp with FastAPI using middleware and event handlers
# app.add_middleware(GitHubAppMiddleware, app=GitHubApp(...))
