# Architecture

How DataGuardian AI turns DataHub metadata into governance decisions, and why
the numbers it produces are reproducible.

Throughout these diagrams: **green is deterministic, amber is generative.**
That colour split is the single most important thing to understand about the
system.

---

## 1. System architecture

```mermaid
graph TD
    subgraph Client
        UI["React Workspace<br/>8 pages · TanStack Query"]
    end

    subgraph Server["FastAPI Backend"]
        API["REST API<br/>13 typed endpoints"]
        AGENT["LangGraph Agent"]
        RISK["Risk Engine<br/>6 weighted rules"]
        TOOLS["Tool Layer<br/>5 agent-facing tools"]
        LLMX["LLM Layer<br/>5 providers"]
        DHI["DataHub Integration<br/>6 layers"]
    end

    subgraph External
        GMS[("DataHub GMS<br/>GraphQL")]
        PROV["Groq · Gemini<br/>Grok · OpenAI · Claude"]
    end

    UI -->|"HTTP /api/v1"| API
    API --> AGENT
    AGENT --> TOOLS
    AGENT --> RISK
    AGENT --> LLMX
    TOOLS --> DHI
    DHI -->|GraphQL| GMS
    LLMX -->|"chat/completions"| PROV

    style RISK fill:#0d3b2e,stroke:#34d399,color:#e6fff7
    style TOOLS fill:#0d3b2e,stroke:#34d399,color:#e6fff7
    style DHI fill:#0d3b2e,stroke:#34d399,color:#e6fff7
    style LLMX fill:#3b2f0d,stroke:#fbbf24,color:#fff9e6
    style PROV fill:#3b2f0d,stroke:#fbbf24,color:#fff9e6
```

**The boundary that matters:** the LLM layer never touches the DataHub
integration. It receives serialised JSON from the Tool layer and nothing else.
That is structural — no node in the graph holds a DataHub client — rather than
a convention someone could accidentally break.

---

## 2. AI workflow

```mermaid
graph LR
    U["👤 Question"] --> P["Planner"]
    P --> T["Tools"]
    T --> R["Risk Engine"]
    R --> L["LLM"]
    L --> REC["Recommendations"]

    style R fill:#0d3b2e,stroke:#34d399,color:#e6fff7
    style T fill:#0d3b2e,stroke:#34d399,color:#e6fff7
    style L fill:#3b2f0d,stroke:#fbbf24,color:#fff9e6
    style REC fill:#3b2f0d,stroke:#fbbf24,color:#fff9e6
```

The facts are gathered and judged before the model is ever called. By the time
the LLM runs, the verdict already exists — its job is to explain it.

---

## 3. LangGraph agent

```mermaid
stateDiagram-v2
    [*] --> Planner

    Planner --> Datasets: plan contains
    Planner --> Owners: plan contains
    Planner --> Lineage: plan contains
    Planner --> Statistics: plan contains
    Planner --> Risk: otherwise

    Datasets --> Owners: plan contains
    Datasets --> Lineage: skip owners
    Datasets --> Risk: skip both

    Owners --> Lineage: plan contains
    Owners --> Risk: skip lineage

    Lineage --> Statistics: plan contains
    Lineage --> Risk: skip statistics

    Statistics --> Risk

    Risk --> Reasoning
    Reasoning --> Recommendation: actionable intent
    Reasoning --> Report: report intent
    Reasoning --> [*]: otherwise

    Recommendation --> [*]
    Report --> [*]
```

**Every edge is conditional.** The planner writes `state["plan"]` — a list of
node names — and each router asks "what is the next pipeline node the plan
actually contains?" Routing lives in *data*, not control flow, so adding an
intent is a mapping entry rather than a pipeline rewrite.

### Tool selection by intent

| Intent | Tools run | Skipped |
| --- | --- | --- |
| `find_missing_owners` | dataset, owner | lineage, statistics |
| `analyze_lineage` | dataset, lineage | owner, statistics |
| `find_risky_datasets` | dataset, owner, lineage | statistics |
| `analyze_governance` | dataset, owner, statistics | lineage |
| `generate_report` | dataset, owner, statistics, report | lineage |
| `generate_documentation` | dataset, statistics | owner, lineage |

Skipped nodes are still recorded in the trace. "It did not call the lineage
tool" is the evidence that the agent plans — hiding it would lose the point.

---

## 4. Request lifecycle

```mermaid
sequenceDiagram
    actor User
    participant UI as React
    participant API as FastAPI
    participant AG as Agent
    participant TL as Tools
    participant DH as DataHub
    participant RE as Risk Engine
    participant LLM

    User->>UI: "Find datasets without owners"
    UI->>API: POST /api/v1/agent/analyze
    API->>AG: analyze(question)

    AG->>AG: Planner: intent + tool selection
    Note over AG: rules first; LLM only on a tie

    AG->>TL: DatasetTool.list()
    TL->>DH: GraphQL listDatasets
    DH-->>TL: metadata
    TL-->>AG: typed models

    AG->>TL: OwnerTool.list()
    TL->>DH: GraphQL aggregateOwners
    DH-->>TL: owner facets
    TL-->>AG: typed models

    Note over AG: lineage + statistics SKIPPED

    AG->>RE: assess(datasets)
    RE-->>AG: score 50, level HIGH, 5 findings

    AG->>LLM: explain(verdict + evidence)
    LLM-->>AG: summary + business impact

    AG->>LLM: recommend(findings)
    LLM-->>AG: corrective actions

    AG-->>API: AgentResult + trace
    API-->>UI: 200 JSON
    UI->>User: answer + execution timeline
```

---

## 5. Failure handling

```mermaid
flowchart TD
    START["Node executes"] --> OK{"Succeeded?"}
    OK -->|Yes| NEXT["Continue"]
    OK -->|No| CONTAIN["executor.run_node contains it"]

    CONTAIN --> MARK["Mark FAILED in trace<br/>set degraded = true"]
    MARK --> CONTINUE["Graph continues<br/>on partial evidence"]
    CONTINUE --> ANSWER["Answer says evidence<br/>is incomplete"]

    LLMFAIL["LLM unreachable"] --> RETRY{"Transient?"}
    RETRY -->|"429 / timeout / 5xx"| FAILOVER["Fail over to<br/>next provider"]
    RETRY -->|"bad key / bad model"| RAISE["Raise immediately"]
    FAILOVER --> DETERM["All providers down →<br/>deterministic summary<br/>from findings"]

    style CONTINUE fill:#0d3b2e,stroke:#34d399,color:#e6fff7
    style DETERM fill:#0d3b2e,stroke:#34d399,color:#e6fff7
    style RAISE fill:#3b1d1d,stroke:#f87171,color:#ffe6e6
```

| Failure | Behaviour |
| --- | --- |
| One tool fails | Node marked FAILED, graph continues, `degraded: true` |
| DataHub down | Findings empty, answer states the evidence is incomplete |
| LLM rate-limited | Automatic fail-over to the next configured provider |
| All LLMs down | Deterministic summary from findings; **score unaffected** |
| Whole graph fails | Still returns the contract, never raises to the API |

**Only transient failures fail over.** A rejected API key would fail
identically on the next provider, so retrying it just burns quota and hides
the real error.

A degraded run returns **HTTP 200**. A partial answer is a *result*, not a
transport failure; non-2xx is reserved for genuine request problems.

---

## 6. DataHub integration layers

```mermaid
graph TD
    S["service.py<br/>public interface · error semantics"] --> C["cache.py<br/>TTL + LRU · single-flight"]
    S --> M["mapper.py<br/>dicts → typed models"]
    S --> Q["queries.py<br/>12 GraphQL documents"]
    S --> G["graphql.py<br/>envelope validation"]
    G --> CL["client.py<br/>pooled HTTP · retries"]
    CL --> GMS[("DataHub GMS")]

    style S fill:#0d3b2e,stroke:#34d399,color:#e6fff7
```

Each layer depends only on those below it. Two properties are load-bearing:

**GraphQL returns HTTP 200 on failure.** `graphql.py` exists so a caller never
reads `data` as `None` and fails later with a confusing mapping error.

**The cache never stores failures.** A DataHub blip cannot be pinned in place
for the whole TTL — the next caller retries for real.

---

## 7. LLM provider layer

```mermaid
graph TD
    F["LLMFactory<br/>LLM_PROVIDER"] --> AUTO{"auto?"}
    AUTO -->|Yes| PICK["First provider<br/>with a key"]
    AUTO -->|No| PIN["Pinned provider"]

    PICK --> CHAIN["FallbackProvider"]
    PIN --> CHAIN

    CHAIN --> P1["Groq"]
    P1 -.->|"429 / timeout"| P2["Gemini"]
    P2 -.->|"429 / timeout"| P3["Grok · OpenAI · Claude"]

    OAC["OpenAICompatibleProvider<br/>shared transport"] --> P1
    OAC --> P2
    OAC --> P3
```

All five providers speak OpenAI's chat-completions protocol, so the transport
— auth, retries, error translation, response mapping — lives in one place and
each provider is a ~20-line configuration file.

Switching model or vendor is a config change:

```bash
LLM_PROVIDER=gemini
LLM_MODEL=gemini-2.5-flash
```

---

## 8. Frontend data flow

```mermaid
graph LR
    C["Component"] --> H["Query hook"]
    H --> SVC["Service"]
    SVC --> WF{"withFallback"}
    WF -->|"Demo Mode ON"| DEMO["Deterministic<br/>catalogue"]
    WF -->|"live call OK"| LIVE["Backend"]
    WF -->|"live call fails"| DEMO

    LIVE --> TAG1["source: live"]
    DEMO --> TAG2["source: demo"]
    TAG1 & TAG2 --> UI["SourceTag in the UI"]

    style TAG1 fill:#0d3b2e,stroke:#34d399,color:#e6fff7
    style TAG2 fill:#3b2f0d,stroke:#fbbf24,color:#fff9e6
```

Every service returns `Sourced<T>` carrying a `source` tag, and every panel
renders it. In a product whose entire pitch is trustworthy governance data,
showing invented figures unlabelled would undermine the thing being
demonstrated.

---

## Further reading

- [`backend/app/agents/README.md`](../backend/app/agents/README.md) — agent internals
- [`backend/app/llm/README.md`](../backend/app/llm/README.md) — adding a provider
- [`backend/app/integrations/datahub/README.md`](../backend/app/integrations/datahub/README.md) — DataHub layers
- [`docs/datahub.md`](datahub.md) — DataHub setup and debugging
- [`docs/demo-script.md`](demo-script.md) — the 4-minute walkthrough
