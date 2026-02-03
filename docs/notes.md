  ┌────────────────────┬─────────────────────────────────────────────────────────────┬─────────────────────────────────────────┐
  │        Area        │                       Custom Workers                        │             GitHub Actions              │
  ├────────────────────┼─────────────────────────────────────────────────────────────┼─────────────────────────────────────────┤
  │ Infrastructure     │ You manage Redis, containers, scaling, monitoring, restarts │ GitHub manages everything               │
  ├────────────────────┼─────────────────────────────────────────────────────────────┼─────────────────────────────────────────┤
  │ Runner maintenance │ Patching, security updates, dependency management           │ GitHub handles updates                  │
  ├────────────────────┼─────────────────────────────────────────────────────────────┼─────────────────────────────────────────┤
  │ Secrets management │ Must secure API keys, tokens in your infra                  │ Built-in encrypted secrets              │
  ├────────────────────┼─────────────────────────────────────────────────────────────┼─────────────────────────────────────────┤
  │ Scaling            │ Manual scaling, container orchestration (K8s?)              │ Auto-scales with usage limits           │
  ├────────────────────┼─────────────────────────────────────────────────────────────┼─────────────────────────────────────────┤
  │ Cost               │ Fixed infra cost regardless of usage                        │ Pay per minute (free tier available)    │
  ├────────────────────┼─────────────────────────────────────────────────────────────┼─────────────────────────────────────────┤
  │ Networking         │ Must expose endpoints, handle firewalls, mTLS               │ No inbound connections needed           │
  ├────────────────────┼─────────────────────────────────────────────────────────────┼─────────────────────────────────────────┤
  │ State management   │ Redis streams, consumer groups, message acks                │ Stateless, GitHub handles retries       │
  ├────────────────────┼─────────────────────────────────────────────────────────────┼─────────────────────────────────────────┤
  │ PR comments        │ Need GitHub App token, API calls, rate limits               │ Native github.token, built-in actions   │
  ├────────────────────┼─────────────────────────────────────────────────────────────┼─────────────────────────────────────────┤
  │ Logs/debugging     │ Build your own logging/tracing                              │ Built-in logs in PR UI                  │
  ├────────────────────┼─────────────────────────────────────────────────────────────┼─────────────────────────────────────────┤
  │ Concurrency        │ Manage consumer groups, avoid duplicate processing          │ Matrix builds, job concurrency controls │
  └────────────────────┴─────────────────────────────────────────────────────────────┴─────────────────────────────────────────┘
  When custom makes sense:
  - Need to run on internal network (access private resources)
  - Scans require licensed tools not available in Actions
  - Want full control over execution environment
  - Need long-running jobs (Actions has 6hr limit)
  - Cost optimization at high volume

  When GitHub Actions wins:
  - Faster time to market
  - Less operational burden
  - Better GitHub integration (checks API, annotations, PR status)
  - Community actions ecosystem (KICS, Blackduck actions already exist)
  - No infrastructure to secure/maintain

  For security scanning, Actions is typically simpler since tools like checkmarx/kics-github-action and synopsys-sig/blackduck-action already exist.

  GitHub Actions (Distributed Model)
  ┌───────────────────────┬─────────────────────────────────────────────────┐
  │         Pros          │                      Cons                       │
  ├───────────────────────┼─────────────────────────────────────────────────┤
  │ Zero infra to manage  │ 100-500 repos need workflow files               │
  ├───────────────────────┼─────────────────────────────────────────────────┤
  │ GitHub scales runners │ Version drift across repos                      │
  ├───────────────────────┼─────────────────────────────────────────────────┤
  │ Native PR integration │ Teams must understand Actions syntax            │
  ├───────────────────────┼─────────────────────────────────────────────────┤
  │                       │ Reusable workflows help but still need adoption │
  ├───────────────────────┼─────────────────────────────────────────────────┤
  │                       │ Org-wide updates = 500 PRs or push access       │
  ├───────────────────────┼─────────────────────────────────────────────────┤
  │                       │ Teams can modify/disable workflows              │
  └───────────────────────┴─────────────────────────────────────────────────┘
  Custom Centralized (Your Approach)
  ┌───────────────────────────────────┬──────────────────────────────────────────┐
  │               Pros                │                   Cons                   │
  ├───────────────────────────────────┼──────────────────────────────────────────┤
  │ Install GitHub App once per org   │ You own the infrastructure               │
  ├───────────────────────────────────┼──────────────────────────────────────────┤
  │ Zero repo changes needed          │ Day 2 ops: monitoring, alerting, on-call │
  ├───────────────────────────────────┼──────────────────────────────────────────┤
  │ Security team has full control    │ Scaling: K8s, auto-scaling, queue depth  │
  ├───────────────────────────────────┼──────────────────────────────────────────┤
  │ Consistent enforcement            │ HA/DR requirements                       │
  ├───────────────────────────────────┼──────────────────────────────────────────┤
  │ Single codebase to update         │ Build GitHub integration yourself        │
  ├───────────────────────────────────┼──────────────────────────────────────────┤
  │ Teams don't need to know anything │ Debugging distributed system             │
  └───────────────────────────────────┴──────────────────────────────────────────┘
  At 100-500 repo scale, the math shifts:

  GitHub Actions:
  - Engineering overhead: onboarding teams, workflow updates, drift
  - Operational overhead: low (GitHub's problem)

  Custom Solution:
  - Engineering overhead: one-time build, single codebase
  - Operational overhead: high (infra, scaling, reliability)

  Hybrid option worth considering:

  Use GitHub App webhook to trigger GitHub Actions workflow via workflow_dispatch:

  PR opened → GitHub App → workflow_dispatch API → triggers shared workflow

  - Security team controls trigger logic centrally
  - No workflow files in each repo
  - GitHub manages runners/scaling
  - Best of both worlds

  Would you like to explore that pattern?
