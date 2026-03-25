Create a new agent in the $ARGUMENTS domain. Follow the pattern in docs/agent-patterns.md.
Steps:
1. Read docs/agent-patterns.md for the template
2. Create the agent file in agents/{domain}/
3. Register it in the domain's supervisor
4. Update orchestrator/graph.py if it's a new domain
5. Add corresponding Pydantic schema if needed
6. Write a test in tests/agents/
7. Run pytest tests/agents/test_{agent_name}.py -v
