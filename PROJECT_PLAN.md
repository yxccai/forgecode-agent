- # ForgeCode — Overall Development Plan

  > **ForgeCode — A minimal repository-aware coding agent built with LangChain and LangGraph.**

  ## 1. Project Goal

  ForgeCode is a lightweight terminal-based Coding Agent designed for two purposes:

  1. Learn the core mechanisms behind modern AI Agents through real implementation.
  2. Become a technically credible portfolio project for Agent / Coding Agent internship interviews.

  ForgeCode is **not** intended to replicate Claude Code, Codex, Cursor, or other production-scale coding agents.

  The goal is to build a system that is:

  * small enough to fully understand;
  * complete enough to demonstrate the essential mechanisms of a Coding Agent;
  * measurable enough to verify whether architectural decisions actually help;
  * clean enough that every major design decision can be explained in an interview.

  The project should optimize for:

  > **Understanding > Feature Count**
  > **Core Mechanisms > Technology Stacking**
  > **Verified Behavior > Impressive Demos**
  > **Simple Architecture > Premature Engineering**

  ---

  # 2. Core Design Philosophy

  ForgeCode should evolve from a minimal tool-calling loop into a repository-aware, stateful, reliable, and measurable Coding Agent.

  The expected capability progression is:

  ```text
  Agent Loop
      ↓
  Tool Use
      ↓
  Coding Actions
      ↓
  State & Persistence
      ↓
  Planning
      ↓
  Repository Context
      ↓
  Memory
      ↓
  Reliable Execution
      ↓
  Verification
      ↓
  Evaluation
  ```

  Every new mechanism must solve a real limitation discovered in the previous version.

  Do not add technology simply because it is popular.

  In particular:

  * do not introduce RAG just to claim RAG support;
  * do not introduce Multi-Agent just to claim Multi-Agent support;
  * do not introduce a vector database unless semantic retrieval is actually useful;
  * do not introduce Docker, Kubernetes, MCP, GraphRAG, or complex infrastructure unless an actual requirement appears;
  * do not hide important Agent behavior behind high-level agent factories before the underlying mechanism has been understood.

  The architecture should **emerge from observed problems**.

  ---

  # 3. Technical Direction

  The overall technical direction is fixed as follows.

  ```text
  Language
      Python
  
  V0
      Direct model API / low-level tool calling
      No high-level Agent framework
  
  V1+
      LangChain
      Messages
      Tools
      Structured interfaces where appropriate
  
  V2+
      LangGraph
      StateGraph
      Explicit state transitions
      Checkpoint / persistence
      Interrupt / resume where appropriate
  
  Repository Intelligence
      Repository structure
      Lexical search
      Symbol-aware search
      Targeted file reading
      Context budgeting
  
  Memory
      Working memory
      Thread/task memory
      Repository semantic memory
      Episodic task memory
  
  Execution
      Local repository
      Git
      Git worktree isolation
      Controlled shell execution
  
  Verification
      Tests
      Lint
      Type checking
      Build/runtime feedback where available
  
  Evaluation
      Reproducible benchmark
      Trajectory logging
      Metrics
      Ablation experiments
      Failure analysis
  ```

  Exact libraries, internal abstractions, schemas, directory layout, and implementation details may be chosen during development when justified by simplicity and clarity.

  ---

  # 4. Development Rule

  Each version must follow this loop:

  ```text
  Problem
     ↓
  Minimal Design
     ↓
  Implementation
     ↓
  Real Task
     ↓
  Trajectory Inspection
     ↓
  Failure Analysis
     ↓
  Improvement
     ↓
  Verification
  ```

  Do not build several future versions at once.

  Each version must remain independently runnable and understandable.

  After completing a version:

  1. run at least one representative task;
  2. inspect the actual Agent trajectory;
  3. explain the important mechanisms;
  4. document major design decisions;
  5. verify the completion criteria;
  6. stop.

  **Do not automatically proceed to the next version.**

  ---

  # 5. Cross-Version Foundations

  Several capabilities should evolve throughout the whole project rather than appearing suddenly in one version.

  ## 5.1 Trajectory

  Every Agent execution should eventually be observable as a trajectory:

  ```text
  Task
    ↓
  Model Decision
    ↓
  Tool Call
    ↓
  Tool Result
    ↓
  Model Decision
    ↓
  ...
    ↓
  Verification
    ↓
  Final Result
  ```

  Trajectories are foundational for:

  * debugging;
  * understanding Agent behavior;
  * evaluation;
  * failure analysis;
  * memory;
  * future training experiments.

  Observability should remain lightweight.

  Do not introduce a large observability platform unless necessary.

  ---

  ## 5.2 Memory

  Memory should evolve naturally.

  ForgeCode should distinguish:

  ```text
  Context
  ≠
  State
  ≠
  Checkpoint
  ≠
  Memory
  ```

  The intended progression is:

  ```text
  V0
  Working memory through message history
  
  V1
  Working-memory management and tool-output compression
  
  V2
  Thread-scoped state, checkpointing, persistence, resume
  
  V3
  Repository semantic memory and episodic task memory
  
  V4
  Memory validation, confidence, freshness and invalidation
  
  V5
  Memory evaluation and ablation
  ```

  Do not begin with a complex vector-memory architecture.

  Simple structured storage such as JSON or SQLite is acceptable until requirements justify something more advanced.

  ---

  ## 5.3 Evaluation

  Evaluation should not exist only at the end.

  From early versions, record inexpensive signals when practical:

  ```text
  steps
  tool calls
  files read
  tests executed
  tokens
  latency
  success/failure
  ```

  V5 will turn these signals into a formal benchmark.

  ---

  # 6. V0 — Minimal Agent

  ## Objective

  Understand the fundamental Agent loop and the boundary between the model and the execution environment.

  The Agent should initially be capable of inspecting a repository but not modifying it.

  Conceptually:

  ```text
  User
   ↓
  Model
   ↓
  Tool Call
   ↓
  Tool Execution
   ↓
  Observation
   ↓
  Model
   ↓
  ...
   ↓
  Final Answer
  ```

  Use only a small set of safe tools, approximately covering:

  ```text
  read file
  search text
  run safe command
  ```

  Avoid LangChain/LangGraph high-level Agent abstractions at this stage.

  The important concepts are:

  * messages;
  * tool schemas;
  * tool calls;
  * tool results;
  * observations;
  * the Agent loop;
  * ReAct-style interaction;
  * working memory;
  * stopping conditions;
  * model/environment boundaries.

  ### Completion Criteria

  ForgeCode can independently perform a simple repository-understanding task by searching, reading, executing safe commands, and producing a grounded answer.

  After V0, the Agent loop should be explainable directly from the source code.

  ---

  # 7. V1 — Coding Agent

  ## Objective

  Turn the minimal Agent into an actual Coding Agent using standard LangChain abstractions.

  LangChain should now be used where it reduces unnecessary framework work without hiding the mechanisms being studied.

  The Agent should gain the ability to:

  ```text
  inspect repository
  search code
  read files
  edit files
  execute commands
  inspect git diff
  run tests
  react to tool failures
  ```

  The central research question is:

  > **How should tools be designed so that an LLM can safely and effectively manipulate software?**

  Important areas include:

  * Tool API design;
  * Tool schema quality;
  * constrained filesystem access;
  * editing strategy;
  * shell execution;
  * error propagation;
  * tool output size;
  * context management.

  Tool interfaces should remain small and orthogonal.

  Do not create many overlapping tools.

  ### Completion Criteria

  ForgeCode can independently solve a simple bug:

  ```text
  Locate
  → Inspect
  → Modify
  → Test
  → Observe
  → Finish
  ```

  The final result must include the real repository diff and verification result.

  ---

  # 8. V2 — Stateful Agent

  ## Objective

  Move from an implicit while-loop architecture toward an explicit, controllable Agent runtime using LangGraph.

  LangGraph should be introduced because longer-running Agent behavior now creates real needs for:

  * explicit state;
  * conditional routing;
  * planning;
  * execution budgets;
  * persistence;
  * interruption;
  * recovery.

  The architecture should make Agent control flow visible rather than hiding it.

  Conceptually:

  ```text
  START
    ↓
  Plan
    ↓
  Act
    ↓
  Tools
    ↓
  Observe
    ↓
  Continue / Verify / Finish
  ```

  Introduce only lightweight planning.

  Planning exists to improve execution, not to create elaborate plans for trivial tasks.

  The Agent must also gain execution budgets such as:

  * maximum steps;
  * maximum tool calls;
  * optional token/cost limits.

  Use LangGraph checkpointing for task persistence.

  Understand and document the relationship between:

  ```text
  State
  Thread
  Checkpoint
  Short-Term Memory
  Resume
  ```

  ### Completion Criteria

  ForgeCode can perform a multi-step coding task and survive process interruption.

  A task can be resumed from persisted state without restarting reasoning from zero.

  ---

  # 9. V3 — Repository Intelligence

  ## Objective

  Study one of the central problems in Coding Agents:

  > **How does an Agent find the right context inside a repository without reading everything?**

  Do not treat this primarily as a generic RAG problem.

  Prefer repository-native signals first.

  Potential mechanisms include:

  ```text
  repository tree
  file metadata
  lexical search / ripgrep
  symbol extraction
  symbol search
  Tree-sitter
  dependency hints
  targeted file reads
  context ranking
  context budgeting
  tool-output compression
  ```

  The Agent should progressively discover the repository rather than load it wholesale.

  The system should explicitly reason about the difference between:

  ```text
  Repository Search
  
  and
  
  Repository Memory
  ```

  Repository Search answers:

  > What source code is relevant right now?

  Repository Memory answers:

  > What useful knowledge has the Agent already learned about this repository?

  Introduce lightweight long-term memory where useful.

  Possible memory classes:

  ### Semantic Repository Memory

  Examples:

  ```text
  project structure
  test locations
  build commands
  architectural conventions
  important module relationships
  generated-file rules
  ```

  ### Episodic Memory

  Examples:

  ```text
  previous task
  attempts
  failures
  root cause
  successful fix
  verification outcome
  ```

  Do not automatically introduce a vector database.

  Storage and retrieval mechanisms should be chosen based on actual requirements.

  ### Completion Criteria

  Choose a repository significantly larger than the V0/V1 demonstration repository.

  ForgeCode should complete tasks by selecting a relatively small set of relevant files rather than reading the entire repository.

  Record at least:

  ```text
  files inspected
  context tokens
  tool calls
  task outcome
  ```

  ---

  # 10. V4 — Reliable Execution

  ## Objective

  Move from:

  > “The Agent can modify code.”

  to:

  > “The Agent can modify code in a controlled and verifiable way.”

  Three areas are mandatory.

  ---

  ## 10.1 Workspace Isolation

  Agent changes should not directly contaminate the user's normal working tree.

  Prefer a lightweight Git-based mechanism such as:

  ```text
  Git repository
        ↓
  temporary worktree
        ↓
  ForgeCode execution
  ```

  A worktree provides workspace isolation.

  It should not be confused with a full security sandbox.

  ---

  ## 10.2 Permission and Human-in-the-Loop

  Tools should have different risk levels.

  Conceptually:

  ```text
  Low Risk
      → automatic execution
  
  Higher Risk
      → explicit approval
  ```

  Use LangGraph interrupt/resume where appropriate.

  The goal is to understand the balance between:

  ```text
  Agent autonomy
  
  and
  
  human control
  ```

  Do not create an unnecessarily complicated permission framework.

  ---

  ## 10.3 Verification Loop

  A Coding Agent should prefer executable evidence over self-assessment.

  Verification may include:

  ```text
  tests
  lint
  type checker
  compiler
  build
  runtime checks
  ```

  The desired loop is:

  ```text
  Edit
   ↓
  Verify
   ↓
  Fail
   ↓
  Feedback
   ↓
  Repair
   ↓
  Verify
   ↓
  Pass
  ```

  The Agent must not treat its own claim of completion as sufficient evidence.

  ### Completion Criteria

  Demonstrate at least one real trajectory where:

  ```text
  first modification
  → verification failure
  → failure analysis
  → second modification
  → verification success
  ```

  Also demonstrate at least one tool execution requiring user approval.

  At this point ForgeCode should already be suitable for a technical portfolio demonstration.

  ---

  # 11. V5 — Evaluation

  ## Objective

  Stop expanding features and determine whether previous architectural decisions actually improve Agent performance.

  Create a small but real Coding Agent benchmark.

  Target approximately:

  ```text
  20–30 tasks
  ```

  Possible task categories:

  ```text
  Bug Fix
  Small Feature
  Refactor
  Test Generation
  Code Understanding
  ```

  Prefer tasks with objective verification whenever possible.

  ---

  ## Metrics

  At minimum record:

  ```text
  Task Success Rate
  Test Pass Rate
  Agent Steps
  Tool Calls
  Token Usage
  Latency
  Files Read
  ```

  Additional metrics may be introduced only when useful.

  ---

  ## Ablation

  Ablations must test specific hypotheses.

  Examples:

  ```text
  ReAct
  vs
  ReAct + Planning
  ```

  Question:

  > Does explicit planning improve difficult multi-step tasks?

  ---

  ```text
  Basic Search
  vs
  Repository-Aware Context Selection
  ```

  Question:

  > Does repository intelligence reduce context usage or improve success?

  ---

  ```text
  Edit → Finish
  vs
  Edit → Verify → Repair
  ```

  Question:

  > Does executable verification improve task success?

  ---

  ```text
  No Persistent Memory
  vs
  Repository Memory
  ```

  Question:

  > Does memory reduce repeated repository exploration or improve success?

  Do not assume that more complex systems will perform better.

  Negative results are valid results.

  ---

  ## Failure Analysis

  Failed tasks should be classified into a small useful taxonomy.

  For example:

  ```text
  Context Failure
  Planning Failure
  Tool-Use Failure
  Code/Edit Failure
  Verification Failure
  Termination Failure
  Infrastructure Failure
  ```

  The taxonomy may evolve based on observed failures.

  ### Completion Criteria

  ForgeCode should be able to answer empirically:

  * Does planning help?
  * Does repository-aware context help?
  * Does verification help?
  * Does persistent memory help?
  * What are the dominant failure modes?
  * What performance improvements increase token usage or latency?
  * Which mechanisms provide little measurable benefit?

  This milestone defines:

  # ForgeCode v1.0

  ---

  # 12. Architecture Principles

  Throughout development, prefer these principles.

  ### Explicit over magical

  Important Agent transitions should be observable and explainable.

  ### Tools over giant prompts

  Give the model appropriate capabilities instead of putting all repository information into the prompt.

  ### Environment feedback over self-reflection

  For software tasks:

  ```text
  pytest > “reflect on whether the code is correct”
  ```

  when executable verification is available.

  ### Repository-native retrieval before generic semantic retrieval

  Code structure, symbols, lexical matches, tests, imports, and repository structure often contain stronger signals than generic embedding similarity.

  ### Structured state, selective context

  The Agent may maintain significant internal state without placing all of it into every LLM context window.

  ### Memory is fallible

  Memory should support:

  ```text
  source
  freshness
  confidence
  validation
  invalidation
  ```

  where useful.

  Repository source code remains authoritative over stale remembered information.

  ### Complexity must earn its existence

  Every substantial component should answer:

  > What failure or limitation does this solve?

  If that question has no clear answer, do not add it yet.

  ---

  # 13. Documentation

  Keep documentation lightweight but intentional.

  Important architectural choices should be recorded as short Architecture Decision Records.

  For example:

  ```text
  Why LangGraph was introduced
  Why Git worktree was chosen
  Why vector search was not initially used
  Why a certain editing strategy was selected
  Why planning was introduced
  Why a memory type exists
  ```

  The objective is not extensive documentation.

  The objective is to preserve reasoning behind the architecture.

  ---

  # 14. Out of Scope for ForgeCode v1.0

  Unless a concrete requirement appears, the following should remain outside the main roadmap:

  ```text
  Web UI
  IDE extension
  Distributed services
  Kubernetes
  Kafka
  Complex cloud infrastructure
  GraphRAG
  Large vector infrastructure
  Large-scale multi-agent orchestration
  Dozens of MCP servers
  Autonomous git push
  Complex knowledge graphs
  Agentic reinforcement learning
  Large-scale fine-tuning
  ```

  These are possible future experiments, not prerequisites for a strong Coding Agent project.

  ---

  # 15. Possible Post-v1.0 Extensions

  Only after V5 evaluation is complete should new capabilities be considered.

  Potential directions include:

  ### MCP

  Integrate one small MCP server and compare MCP tools with native ForgeCode tools.

  ### Security Sandbox

  Move command execution from worktree isolation toward stronger process/container isolation.

  ### Multi-Agent

  Introduce another specialized Agent only if evaluation reveals a concrete failure mode that separation of roles may solve.

  ### Agent Learning

  Use collected trajectories and verification outcomes to explore:

  ```text
  trajectory filtering
  SFT
  verifiers
  reward modeling
  Agentic RL
  ```

  This should only happen after ForgeCode has a meaningful environment, task set, trajectory dataset, and evaluation system.

  ---

  # 16. Definition of Success

  ForgeCode is successful if, by v1.0, its developer can clearly explain:

  ```text
  How an Agent loop works
  
  How tool calling connects an LLM to an environment
  
  How tool design changes Agent behavior
  
  Why stateful execution is useful
  
  Why and when LangGraph is useful
  
  How planning interacts with acting
  
  What Context, State, Memory, Thread and Checkpoint mean
  
  How repository context is selected
  
  How repository memory differs from repository search
  
  How a Coding Agent modifies code safely
  
  How environment feedback drives repair
  
  Why verification matters
  
  How Agent behavior is evaluated
  
  How architectural choices are tested through ablation
  
  What the system's dominant failure modes are
  ```

  The strongest outcome is not the number of supported features.

  The strongest outcome is:

  > **Every important mechanism exists for a reason, can be demonstrated through a real trajectory, and can be evaluated with evidence.**

  ---

  # 17. Instruction to the Implementing Agent

  When implementing ForgeCode:

  1. Preserve the architecture and learning objectives described in this document.
  2. Prefer the simplest correct solution.
  3. Make reasonable engineering decisions independently when implementation details are unspecified.
  4. Do not prematurely implement future-version features.
  5. Do not introduce infrastructure without a demonstrated requirement.
  6. Keep major mechanisms observable and explainable.
  7. Prefer real repository behavior and executable verification over mocked demonstrations.
  8. Keep trajectory and evaluation data sufficiently structured for later analysis.
  9. Preserve clean boundaries between model reasoning, tools, execution environment, state, memory, context, and verification.
  10. At the end of each version, stop and produce:

  * the implemented architecture;
  * a representative execution;
  * major design decisions;
  * known limitations;
  * completion-criteria results.

  
