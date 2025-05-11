from google.adk.agents.llm_agent import LlmAgent
from google.adk.runners import Runner
from google.adk.artifacts import InMemoryArtifactService
from google.adk.sessions import InMemorySessionService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.genai import types
from typing import Dict, Any, AsyncIterable
import os
import json
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioServerParameters
from google.adk.models.lite_llm import LiteLlm
from dotenv import load_dotenv

load_dotenv()

class Agent:
    def __init__(self):
        self._agent = None
        self._exit_stack = None
        self._user_id = "remote_agent"
        self._runner = None

    @classmethod
    async def create(cls):
        """Factory method to create and initialize an Agent instance."""
        self = cls()
        self._agent, self._exit_stack = await self.get_agent_async()
        self._runner = Runner(
            app_name=self._agent.name,
            agent=self._agent,
            artifact_service=InMemoryArtifactService(),
            session_service=InMemorySessionService(),
            memory_service=InMemoryMemoryService(),
        )
        return self
        
    async def get_agent_async(self):
        """Creates an ADK Agent equipped with tools from the MCP Server."""
        if not os.getenv("GOOGLE_MAPS_API_KEY"):
            raise RuntimeError("GOOGLE_MAPS_API_KEY environment variable is required. Please set it in your environment or .env file.")
        # Load agent config from JSON file
        config_path = os.path.join(os.path.dirname(__file__), 'agent_config.json')
        with open(config_path, 'r') as f:
            config = json.load(f)
        agent_data = config.get('agent', {})
        
        # Initialize Brave Search tools
        tools, exit_stack = await MCPToolset.from_server(
            connection_params=StdioServerParameters(
                command='npx',
                args=["-y", 
                      "@modelcontextprotocol/server-google-maps"],
                env={
                    "GOOGLE_MAPS_API_KEY": os.getenv("GOOGLE_MAPS_API_KEY")
                }
            )
        )
        print(f"Fetched {len(tools)} tools from MCP server.")
        if agent_data.get('model', 'gemini-2.0-flash').startswith('gemini'):
            model = agent_data.get('model', 'gemini-2.0-flash')
        else:
            model = LiteLlm(model=agent_data.get('model', 'gemini-2.0-flash'))
        root_agent = LlmAgent(
            model=model,
            name=agent_data.get('name', 'search_agent'),
            description=agent_data.get('description', 'A search assistant that can perform web and local searches using Brave Search.'),
            instruction=agent_data.get('instruction', 'You are a helpful assistant.'),
            tools=tools,
        )
        return root_agent, exit_stack
    
    async def stream(self, query: str, session_id: str) -> AsyncIterable[Dict[str, Any]]:
        try:
            session = self._runner.session_service.get_session(
                app_name=self._agent.name, user_id=self._user_id, session_id=session_id
            )
            content = types.Content(
                role="user", parts=[types.Part.from_text(text=query)]
            )
            if session is None:
                session = self._runner.session_service.create_session(
                    app_name=self._agent.name,
                    user_id=self._user_id,
                    state={},
                    session_id=session_id,
                )
            async for event in self._runner.run_async(
                user_id=self._user_id, session_id=session.id, new_message=content
            ):
                if event.is_final_response():
                    response = ""
                    if (
                        event.content
                        and event.content.parts
                        and event.content.parts[0].text
                    ):
                        response = "\n".join([p.text for p in event.content.parts if p.text])
                    elif (
                        event.content
                        and event.content.parts
                        and any([True for p in event.content.parts if p.function_response])):
                        response = next((p.function_response.model_dump() for p in event.content.parts))
                    yield {
                        "is_task_complete": True,
                        "content": response,
                    }
                else:
                    yield {
                        "is_task_complete": False,
                        "updates": "Processing the request...",
                    }
        except Exception as e:
            yield {
                "error": str(e),
                "is_task_complete": True
            }
        
