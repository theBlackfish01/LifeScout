# Agent Patterns

## Agent Types

Four distinct patterns exist. Every new agent must use one of these.

### Type 1: Pure Prompt (No Tools)

Single LLM call, no tool loop. Used for advisory/planning agents.

```python
def my_agent_node(state: AgentState) -> dict:
    messages = state.get("messages", [])
    profile = ProfileManager().load()
    artifacts = ArtifactLoader.load_recent("{domain}")
    memory = MemoryDistiller.load_summary()

    sys_msg = SystemMessage(content=f"{SYSTEM_PROMPT}\n\nCross-Domain Context:\n{memory}\n\nRecent Artifacts:\n{artifacts}\n\nCurrent User Profile:\n{profile_json}")
    formatted = [sys_msg] + messages

    response = llm.invoke(formatted)

    # Save artifact
    artifact_dir = Path(settings.data_dir) / "{domain}" / "artifacts"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    task_id = state.get("task_id", "manual")
    file_path = artifact_dir / f"{agent_type}_{task_id}.md"
    with open(file_path, "w") as f:
        f.write(response.content)

    return {"messages": [AIMessage(content=f"Generated...", name="{agent_name}")]}
```

**Agents using this pattern:** career_planning, goals, habits, health, therapy, study_plan, progress

### Type 2: ReAct (Tool-Calling Loop)

Uses `create_react_agent(llm, tools)` from LangGraph. Agent loops until tools exhausted or answer found.

```python
from langgraph.prebuilt import create_react_agent

llm = ChatGoogleGenerativeAI(model=settings.model_high_complexity, api_key=settings.gemini_api_key)
tools = [tavily_search, search_jobs, robust_web_scrape]  # pick relevant tools
react_agent = create_react_agent(llm, tools)

def my_agent_node(state: AgentState) -> dict:
    # ... same context injection as Type 1 ...
    input_msgs = [SystemMessage(content=sys_content)] + messages

    try:
        result = react_agent.invoke({"messages": input_msgs})
        ai_messages = [m for m in result["messages"] if isinstance(m, AIMessage) and m.content and not m.tool_calls]
        final_content = ai_messages[-1].content if ai_messages else "Done."
    except Exception as e:
        final_content = f"Error: {str(e)}"

    # Save artifact (same as Type 1)
    return {"messages": [AIMessage(content=f"Generated...", name="{agent_name}")]}
```

**Agents using this pattern:** resume, job_search, interview_prep, linkedin, lead_generation, course_rec

**Tool assignments:**
| Agent | Tools |
|-------|-------|
| resume | tavily_search |
| job_search | search_jobs, tavily_search, robust_web_scrape |
| interview_prep | tavily_search |
| linkedin | tavily_search |
| lead_generation | search_jobs, tavily_search, robust_web_scrape |
| course_rec | search_courses, tavily_search, robust_web_scrape |

### Type 3: Multi-Turn Tool Binding (Onboarding)

Uses `llm.bind_tools([...])` for structured data collection across multiple turns.

```python
llm_with_tools = llm.bind_tools([save_final_profile])

def onboarding_agent_node(state: AgentState) -> dict:
    messages = state.get("messages", [])
    formatted = [SystemMessage(content=PROMPT)] + messages if no system msg

    response = llm_with_tools.invoke(formatted)

    final_messages = [response]
    next_node = "onboarding_agent"  # Self-loop until done

    if hasattr(response, "tool_calls") and response.tool_calls:
        for tool_call in response.tool_calls:
            if tool_call["name"] == "save_final_profile":
                result = save_profile_tool(tool_call["args"])
                if "SUCCESS" in result:
                    next_node = "__end__"
    else:
        # Fallback: regex JSON extraction for Gemini formatting quirks
        # Parse JSON from markdown code blocks or raw content
        ...

    return {"messages": final_messages, "next": next_node}
```

**Agents using this pattern:** onboarding

### Type 4: State Update (Settings)

Uses `llm.bind_tools([...])` to modify persistent state (profile).

```python
llm_with_tools = llm.bind_tools([execute_profile_update])

def settings_agent_node(state: AgentState) -> dict:
    profile = ProfileManager().load()
    sys_prompt = SETTINGS_SYSTEM_PROMPT.format(current_profile=profile_json)
    # ... similar to Type 3 with self-loop ...
    return {"messages": final_messages, "next": next_node}
```

**Agents using this pattern:** settings

## Adding a New Agent

### Step 1: Create Agent File

Create `agents/{domain}/{agent_name}.py`:
- Define `SYSTEM_PROMPT` as a module-level constant (< 2000 tokens)
- Define `{agent_name}_node(state: AgentState) -> dict` using one of the four patterns
- Always inject profile + artifacts + memory into system message
- Always save output to `data/{domain}/artifacts/{type}_{task_id}.md`
- Return `{"messages": [AIMessage(content=..., name="{agent_name}")]}`

### Step 2: Update Domain Supervisor

In `agents/{domain}/supervisor.py`:
- Add agent name to `Route.next` Literal type
- Add agent description to supervisor system prompt
- Import the agent node function

### Step 3: Update Domain Branch

In `orchestrator/graph.py`:
- Import agent node function
- Add node: `graph.add_node("{agent_name}", agent_node_function)`
- Add edges: `{agent_name} → supervisor` and supervisor conditional can route to it

### Step 4: Update Supervisor Prompt

Add the new agent to the supervisor's routing prompt with a clear description of when to route to it.

## Invariants

- All agent node functions return `dict` compatible with `AgentState`
- Agent names in `AIMessage.name` must match graph node names
- System prompts are constants, never dynamically generated (only context injection varies)
- ReAct agents wrap `create_react_agent` invocation in try/except
- Pure prompt agents use `model_low_complexity`, ReAct agents use `model_high_complexity`
- Therapy agent must include safety disclaimer
- Health agent must include medical disclaimer
- Artifacts always named `{type}_{task_id}.md`
