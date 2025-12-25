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

This sequence diagram shows the complete flow from when a user creates a pull request to when the bot posts a comment with analysis results.

```mermaid
sequenceDiagram
    actor User
    participant GH as GitHub
    participant Smee as Smee.io<br/>(smee.io/channel-12345)
    participant SC as Smee Client<br/>(Docker Container)
    participant API as FastAPI App<br/>(web-app Container)
    participant BG as Background Thread<br/>(ThreadPoolExecutor)
    participant Cache as TokenCache
    participant Repo as RepositoryManager
    participant FS as File System<br/>(/tmp/)

    User->>GH: Create Pull Request
    activate GH
    Note over GH: pull_request.opened event
    GH->>Smee: POST webhook event
    deactivate GH

    activate Smee
    Note over Smee: Stores event in channel
    Smee-->>GH: 200 OK
    deactivate Smee

    SC->>Smee: Poll for events
    activate SC
    activate Smee
    Smee-->>SC: Return webhook payload
    deactivate Smee

    SC->>API: POST /webhooks/github
    activate API
    Note over API: GitHubApp middleware<br/>validates signature

    API->>API: Parse payload into<br/>PullRequestPayload
    API->>BG: executor.submit(process_pr_sync)
    activate BG

    API-->>SC: 200 {"status": "accepted"}
    deactivate API
    SC-->>Smee: Forward response
    deactivate SC

    Note over BG: Background processing starts

    BG->>Cache: get_token(install_id)
    activate Cache
    alt Token cached and valid
        Cache-->>BG: Return cached token
    else Token expired or missing
        Cache->>GH: Get installation token
        activate GH
        GH-->>Cache: Access token + expires_at
        deactivate GH
        Cache->>Cache: Cache token<br/>(5 min buffer)
        Cache-->>BG: Return new token
    end
    deactivate Cache

    BG->>Repo: Create RepositoryManager
    activate Repo

    Repo->>Repo: setup()
    Note over Repo: Construct authenticated URL<br/>with token

    Repo->>GH: git clone with token
    activate GH
    GH-->>Repo: Repository contents
    deactivate GH

    Repo->>FS: Clone to /tmp/repo-pr-sha
    activate FS
    FS-->>Repo: Clone complete

    Repo->>Repo: git checkout branch
    Repo-->>BG: Return clone_dir path

    BG->>BG: analyze_repository_structure()
    Note over BG: Recursively count<br/>files & directories

    BG->>FS: os.walk(clone_dir)
    FS-->>BG: File and directory list

    BG->>BG: Calculate stats:<br/>file_count, dir_count

    BG->>Repo: post_comment(client, stats)

    Repo->>GH: POST /repos/{owner}/{repo}/issues/{pr}/comments
    activate GH
    Note over GH: Bot comment with<br/>analysis results
    GH-->>Repo: Comment created
    deactivate GH

    Repo->>FS: cleanup() - delete clone_dir
    FS-->>Repo: Directory removed
    deactivate FS
    deactivate Repo

    Note over BG: Background processing complete
    deactivate BG

    GH->>User: Notify: New comment on PR
    Note over User: User sees bot comment<br/>with file/directory counts
```

## Background Processing Flowchart

This flowchart shows the decision points and process flow in the background worker thread.

```mermaid
flowchart TD
    Start([Webhook Received]) --> Validate{Validate<br/>Signature?}

    Validate -->|Invalid| Reject[Return 401 Unauthorized]
    Validate -->|Valid| Accept[Return 200 Accepted]

    Accept --> Queue[Submit to ThreadPool]
    Queue --> Parse[Parse Webhook Payload<br/>PullRequestPayload.from_webhook]

    Parse --> ValidPR{PR Valid for<br/>Processing?}
    ValidPR -->|No: closed/merged| LogSkip[Log: Skipping PR]
    ValidPR -->|Yes: open| CheckCache{Token in<br/>Cache?}

    CheckCache -->|Yes: valid| UseCache[Use Cached Token]
    CheckCache -->|No or expired| FetchToken[Fetch New Token<br/>from GitHub API]

    FetchToken --> CacheToken[Cache Token<br/>with 5-min buffer]
    CacheToken --> CreateMgr[Create RepositoryManager]
    UseCache --> CreateMgr

    CreateMgr --> AuthURL[Construct Authenticated<br/>Clone URL]
    AuthURL --> Clone[Git Clone Repository<br/>to /tmp/repo-pr-sha]

    Clone -->|Success| Checkout[Git Checkout PR Branch]
    Clone -->|Failure| ErrorClone[Log Error:<br/>Clone Failed]

    Checkout --> Analyze[Analyze Repository Structure<br/>Count files & directories]
    Analyze --> Format[Format Comment Template<br/>with stats]

    Format --> Post[POST Comment to PR<br/>via GitHub API]
    Post -->|Success| LogSuccess[Log: Comment Posted]
    Post -->|Failure| LogError[Log: Comment Failed]

    LogSuccess --> Cleanup[Cleanup: Delete<br/>Clone Directory]
    LogError --> Cleanup
    ErrorClone --> Cleanup
    LogSkip --> End([Processing Complete])

    Cleanup --> End
    Reject --> End

    style Start fill:#e1f5ff,stroke:#0066cc,stroke-width:3px
    style End fill:#e8f5e9,stroke:#4caf50,stroke-width:3px
    style Reject fill:#ffebee,stroke:#f44336,stroke-width:2px
    style ErrorClone fill:#ffebee,stroke:#f44336,stroke-width:2px
    style LogError fill:#fff3e0,stroke:#ff9800,stroke-width:2px
    style Accept fill:#f3e5f5,stroke:#9c27b0,stroke-width:2px
    style LogSuccess fill:#e8f5e9,stroke:#4caf50,stroke-width:2px
```

## Pull Request State Diagram

This state diagram shows the lifecycle of a pull request as it's processed by the GitHub App.

```mermaid
stateDiagram-v2
    [*] --> PR_Created: User creates PR

    PR_Created --> Webhook_Received: pull_request.opened /<br/>pull_request.synchronize

    Webhook_Received --> Validating: Signature check

    Validating --> Rejected: Invalid signature
    Validating --> Queued: Valid signature

    Queued --> Processing: Thread available

    state Processing {
        [*] --> Parsing
        Parsing --> Validation: Extract payload

        Validation --> Skipped: PR closed/merged
        Validation --> TokenFetch: PR is open

        TokenFetch --> Cloning: Token acquired

        state Cloning {
            [*] --> AuthURL: Build clone URL
            AuthURL --> GitClone: Execute git clone
            GitClone --> Checkout: Clone success
            Checkout --> [*]: Branch checked out
        }

        Cloning --> Analyzing: Repository ready
        Cloning --> Failed: Clone error

        state Analyzing {
            [*] --> Scanning: Walk directory tree
            Scanning --> Counting: Count files/dirs
            Counting --> [*]: Stats collected
        }

        Analyzing --> Commenting: Analysis complete

        state Commenting {
            [*] --> Format: Format comment
            Format --> PostAPI: POST to GitHub
            PostAPI --> [*]: Comment created
        }

        Commenting --> Cleanup: Comment posted
        Failed --> Cleanup: Error occurred
        Skipped --> Cleanup: No processing needed

        Cleanup --> [*]: Directory removed
    }

    Processing --> Completed: Success
    Processing --> Error: Exception thrown

    Rejected --> [*]
    Completed --> [*]
    Error --> [*]

    note right of Webhook_Received
        Smee.io forwards webhook
        to local FastAPI app
    end note

    note right of Queued
        Immediate 200 response sent
        ThreadPoolExecutor handles
        background processing
    end note

    note right of Processing
        All operations in
        background thread
        with try-finally cleanup
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
