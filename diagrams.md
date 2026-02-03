# Architecture Diagrams

## System Architecture

This diagram shows the complete architecture of the GitHub App, including Docker containers, application components, and data flow.

```mermaid
graph TB
    subgraph "External Services"
        GH[GitHub]
        SMEE_IO[Smee.io Proxy]
    end

    subgraph "Docker Compose Network<br/>(github-app-network)"
        subgraph "Smee Container"
            SMEE[Smee Client<br/>Webhook Forwarder]
        end

        subgraph "Web-App Container"
            API[FastAPI Application<br/>app.py]
            GHAPP[GitHubApp Middleware]
            EXECUTOR[ThreadPoolExecutor<br/>max_workers=3]

            subgraph "Core Components"
                CACHE[TokenCache<br/>cache.py]
                REPO_MGR[RepositoryManager<br/>repo.py]
                MODEL[PullRequestPayload<br/>model.py]
                UTILS[Utils<br/>utils.py]
            end
        end
    end

    subgraph "Temporary Storage"
        TMP["/tmp/repo-pr-sha"]
    end

    %% External flow
    GH -->|PR Events| SMEE_IO
    SMEE_IO -->|Webhook| SMEE
    SMEE -->|HTTP POST<br/>/webhooks/github| GHAPP

    %% Internal flow
    GHAPP -->|Validate Signature| API
    API -->|Parse Payload| MODEL
    API -->|Submit Task| EXECUTOR

    EXECUTOR -->|Background Process| CACHE
    CACHE -->|Get/Cache Token| GHAPP
    EXECUTOR -->|Create| REPO_MGR

    REPO_MGR -->|Clone & Checkout| TMP
    REPO_MGR -->|Analyze Structure| UTILS
    UTILS -->|Count Files/Dirs| TMP
    REPO_MGR -->|Post Comment| GH
    REPO_MGR -->|Cleanup| TMP

    %% Styling
    classDef external fill:#e1f5ff,stroke:#0066cc,stroke-width:2px
    classDef container fill:#fff4e6,stroke:#ff9800,stroke-width:2px
    classDef component fill:#f3e5f5,stroke:#9c27b0,stroke-width:2px
    classDef storage fill:#e8f5e9,stroke:#4caf50,stroke-width:2px

    class GH,SMEE_IO external
    class SMEE,API,GHAPP,EXECUTOR container
    class CACHE,REPO_MGR,MODEL,UTILS component
    class TMP storage
```

## Pull Request Processing Flow

This sequence diagram shows the high-level flow from when a user creates a pull request to when the bot posts a status comment.

```mermaid
sequenceDiagram
    actor User
    participant GH as GitHub
    participant Smee as Smee.io
    participant SC as Smee Client
    participant API as FastAPI App
    participant BG as Background Thread

    User->>GH: Create Pull Request
    activate GH
    Note over GH: pull_request event
    GH->>Smee: POST webhook event
    deactivate GH

    activate Smee
    Smee-->>GH: 200 OK
    deactivate Smee

    SC->>Smee: Poll for events
    activate SC
    activate Smee
    Smee-->>SC: Return webhook payload
    deactivate Smee

    SC->>API: POST /webhooks/github
    activate API
    Note over API: Validate signature

    API->>API: Parse payload
    API->>BG: Submit to background thread
    activate BG

    API-->>SC: 200 Accepted
    deactivate API
    SC-->>Smee: Forward response
    deactivate SC

    Note over BG: Background processing

    BG->>GH: Clone repository
    activate GH
    GH-->>BG: Repository cloned
    deactivate GH

    BG->>BG: Checkout PR branch

    BG->>BG: Analyze repository

    alt Analysis successful
        BG->>GH: POST comment with results
        activate GH
        Note over GH: Success status
        GH-->>BG: Comment posted
        deactivate GH
    else Analysis failed
        BG->>GH: POST comment with error
        activate GH
        Note over GH: Error status
        GH-->>BG: Comment posted
        deactivate GH
    end

    BG->>BG: Cleanup cloned folder

    Note over BG: Processing complete
    deactivate BG

    GH->>User: Notify: New comment on PR
    Note over User: User sees status comment
```

## Background Processing Flowchart

This flowchart shows the high-level process flow when a pull request event is received.

```mermaid
flowchart TD
    Start([Webhook Received]) --> Validate{Validate<br/>Signature?}

    Validate -->|Invalid| Reject[Return 401 Unauthorized]
    Validate -->|Valid| Accept[Return 200 Accepted]

    Accept --> Queue[Submit to Background Thread]
    Queue --> Parse[Parse Webhook Payload]

    Parse --> ValidPR{PR Open?}
    ValidPR -->|No: closed/merged| Skip[Skip Processing]
    ValidPR -->|Yes| Clone[Clone Repository<br/>to Temp Folder]

    Clone -->|Success| Checkout[Checkout PR Branch]
    Clone -->|Failure| Error[Processing Failed]

    Checkout --> Analyze[Analyze Repository]

    Analyze -->|Success| PostSuccess[Post Comment:<br/>Analysis Results]
    Analyze -->|Failure| PostFail[Post Comment:<br/>Error Status]

    PostSuccess --> Cleanup[Cleanup:<br/>Delete Cloned Folder]
    PostFail --> Cleanup

    Error --> End([Processing Complete])
    Skip --> End
    Cleanup --> End
    Reject --> End

    style Start fill:#e1f5ff,stroke:#0066cc,stroke-width:3px
    style End fill:#e8f5e9,stroke:#4caf50,stroke-width:3px
    style Reject fill:#ffebee,stroke:#f44336,stroke-width:2px
    style Error fill:#ffebee,stroke:#f44336,stroke-width:2px
    style Accept fill:#f3e5f5,stroke:#9c27b0,stroke-width:2px
    style PostSuccess fill:#e8f5e9,stroke:#4caf50,stroke-width:2px
    style PostFail fill:#fff3e0,stroke:#ff9800,stroke-width:2px
```

## Pull Request State Diagram

This state diagram shows the lifecycle of a pull request as it's processed by the GitHub App.

```mermaid
stateDiagram-v2
    [*] --> PR_Created: User creates PR

    PR_Created --> Webhook_Received: pull_request event

    Webhook_Received --> Validating: Signature check

    Validating --> Rejected: Invalid signature
    Validating --> Queued: Valid signature

    Queued --> Processing: Background thread starts

    state Processing {
        [*] --> Parsing
        Parsing --> Validation: Extract payload

        Validation --> Skipped: PR closed/merged
        Validation --> Cloning: PR is open

        Cloning --> Checkout: Clone success
        Cloning --> Failed: Clone error

        Checkout --> Analyzing: Branch checked out

        Analyzing --> Commenting: Analysis complete
        Analyzing --> Failed: Analysis error

        Commenting --> Cleanup: Comment posted
        Failed --> Cleanup: Post error comment
        Skipped --> [*]: No action needed

        Cleanup --> [*]: Temp folder deleted
    }

    Processing --> Completed: Success
    Processing --> Error: Exception

    Rejected --> [*]
    Completed --> [*]
    Error --> [*]

    note right of Webhook_Received
        Smee.io forwards webhook
        to local FastAPI app
    end note

    note right of Queued
        Immediate 200 response
        Background processing starts
    end note
```

## Architecture Components

### 1. Docker Services
Defined in `docker-compose.yaml`:
- **web-app**: FastAPI application container (port 8080:8000)
- **smee**: Webhook proxy container forwarding GitHub events to local app
- **github-app-network**: Bridge network connecting both containers

### 2. Request Flow
1. GitHub sends PR events (opened/synchronize)
2. Events route through Smee.io proxy service
3. Smee container forwards to web-app at `/webhooks/github`
4. GitHubApp middleware validates webhook signature
5. FastAPI handler submits task to background thread pool
6. Background worker processes the PR event

### 3. Background Processing Pipeline
Located in `app.py:54-91`:
1. **Parse Payload** - Extract PR data using PullRequestPayload model
2. **Get Token** - Retrieve cached or fetch new GitHub App installation token
3. **Clone Repository** - Clone to `/tmp/{repo}-{pr_number}-{short_sha}`
4. **Analyze Structure** - Count files and directories (excluding .git)
5. **Post Comment** - Add bot comment to PR with analysis results
6. **Cleanup** - Remove cloned repository from /tmp

### 4. Core Classes

#### TokenCache (`src/cache.py`)
- Thread-safe token caching with threading.Lock
- 5-minute expiration buffer before token expires
- Automatic refresh when expired
- Handles timezone-aware and naive datetime objects

#### RepositoryManager (`src/repo.py`)
- Repository cloning with GitHub App token authentication
- Branch checkout for PR head
- Repository structure analysis
- PR comment posting via GitHub API
- Automatic cleanup after processing

#### PullRequestPayload (`src/model.py`)
- Parses GitHub webhook payload
- Extracts: install_id, repository, branch, commit_sha, PR number, state
- Validates PR is open and not merged/closed
- Provides structured access to webhook data

#### Utils (`src/utils.py`)
- Base64 key decoding for private key
- Datetime parsing with multiple format support
- Repository structure analysis (recursive file/directory counting)
- File I/O utilities

### 5. Environment Configuration
Required environment variables (passed to web-app container):
- `GITHUB_APP_ID` - GitHub App identifier
- `GITHUB_APP_PRIVATE_KEY` - Base64-encoded private key
- `GITHUB_WEBHOOK_SECRET` - Webhook signature validation secret
- `SMEE_URL` - Smee.io proxy URL (for smee container)
- `SMEE_TARGET` - Target URL for webhook forwarding

### 6. Key Features
- **Asynchronous Processing**: ThreadPoolExecutor prevents webhook timeout
- **Token Efficiency**: Caching reduces GitHub API calls
- **Resource Management**: Automatic cleanup of cloned repositories
- **Unique Clone Paths**: Prevents conflicts with commit SHA in path
- **Comprehensive Analysis**: Recursive directory traversal with .git exclusion
