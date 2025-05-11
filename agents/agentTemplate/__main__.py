from server.server import A2AServer
from a2a_types import AgentCard, AgentCapabilities, AgentSkill
from .task_manager import AgentTaskManager
from .agent import Agent
import click
import os
import logging
from dotenv import load_dotenv
import json

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@click.command()
@click.option("--host", default="localhost")
@click.option("--port", default=10002)
def main(host, port):
    # Load config from JSON file
    config_path = os.path.join(os.path.dirname(__file__), 'agent_config.json')
    with open(config_path, 'r') as f:
        config = json.load(f)

    skill_data = config.get('skill', {})
    agent_card_data = config.get('agent_card', {})

    skill = AgentSkill(
        id=skill_data.get('id', 'default-skill-id'),
        name=skill_data.get('name', 'Default Skill Name'),
        description=skill_data.get('description', ''),
        examples=skill_data.get('examples', []),
        inputModes=skill_data.get('inputModes', []),
        outputModes=skill_data.get('outputModes', [])
    )
    agent_card = AgentCard(
        name=agent_card_data.get('name', 'Default Agent'),
        description=agent_card_data.get('description', ''),
        url=f"http://{host}:{port}/",
        version=agent_card_data.get('version', '1.0.0'),
        capabilities=AgentCapabilities(**agent_card_data.get('capabilities', {})),
        skills=[skill],
    )
    server = A2AServer(
        agent_card=agent_card,
        task_manager=AgentTaskManager(agent=Agent()),
        host=host,
        port=port,
    )
    server.start()
    
if __name__ == "__main__":
    main()
