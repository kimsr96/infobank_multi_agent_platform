from google.adk.agents.llm_agent import LlmAgent
from google.adk.runners import Runner
from google.adk.artifacts import InMemoryArtifactService
from google.adk.sessions import InMemorySessionService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.genai import types
from typing import Dict, Any, AsyncIterable
import os
import json
from google.adk.models.lite_llm import LiteLlm

class Agent:
    def __init__(self):
        self._agent = self.__build_agent()
        self._user_id = "remote_agent" 
        
        self._runner = Runner(
            app_name=self._agent.name,
            agent=self._agent,
            artifact_service=InMemoryArtifactService(),  # For files (not used here)
            session_service=InMemorySessionService(),    # Keeps track of conversations
            memory_service=InMemoryMemoryService(),      # Optional: remembers past messages
        )
        
        
    def __build_agent(self) -> LlmAgent:
        # Load agent config from JSON file
        config_path = os.path.join(os.path.dirname(__file__), 'agent_config.json')
        if not os.path.exists(config_path):
            raise ValueError("agent_config.json not found")
        with open(config_path, 'r') as f:
            config = json.load(f)
        if 'agent' not in config:
            raise ValueError("agent not found in agent_config.json")
        agent_data = config.get('agent', {})
        model_name = agent_data.get('model', 'gemini-1.5-flash-latest')
        if model_name.startswith('gemini'):
            model = model_name
        else:
            model = LiteLlm(model=model_name)
        return LlmAgent(
            model=model,
            name=agent_data.get('name', 'agent_template'),
            description=agent_data.get('description', 'A template agent'),
            instruction=agent_data.get('instruction', 'You are a template agent.')
        )
    
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
        
