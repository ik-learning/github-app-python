import os
from fastapi import FastAPI
from githubapp import GitHubApp
# GitHubAppMiddleware, GitHubAppEventHandler

app = FastAPI()

@app.get("/status")
def index():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)), log_level="info", reload=True)

# TODO: Integrate GitHubApp with FastAPI using middleware and event handlers
# app.add_middleware(GitHubAppMiddleware, app=GitHubApp(...))
