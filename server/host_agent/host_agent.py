import os
import json
import uuid
from typing import List
from google.adk import Agent
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.agents.callback_context import CallbackContext
from google.adk.tools.tool_context import ToolContext
from google.adk.tools import agent_tool
from .remote_agent_connection import ( RemoteAgentConnections, TaskUpdateCallback)
from a2a_types import (
    AgentCard,
    Message,
    TaskState,
    TaskSendParams,
    TextPart,
)
from client import A2ACardResolver
from dotenv import load_dotenv
from app.task_queue import task_queue
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm

load_dotenv()

class HostAgent:
  """The host agent.

  This is the agent responsible for choosing which remote agents to send
  tasks to and coordinate their work.
  """

  def __init__(
      self,
      remote_agent_addresses: List[str],
      task_callback: TaskUpdateCallback | None = None
  ):
    
    # config 파일 불러오기
    config_path = os.path.join(os.path.dirname(__file__), 'agent_config.json')
    with open(config_path, 'r') as f:
        config = json.load(f)
    self.config = config
    if 'host_agent' not in self.config:
      raise ValueError("host_agent not found in agent_config.json")
    if 'validator_agent' not in self.config:
      raise ValueError("validator_agent not found in agent_config.json")
    self.host_agent_config = self.config['host_agent']
    self.validator_agent_config = self.config['validator_agent']
    
    self.task_callback = task_callback
    self.remote_agent_connections: dict[str, RemoteAgentConnections] = {}
    self.cards: dict[str, AgentCard] = {}
    for address in remote_agent_addresses:
      card_resolver = A2ACardResolver(address)
      card = card_resolver.get_agent_card()
      remote_connection = RemoteAgentConnections(card)
      self.remote_agent_connections[card.name] = remote_connection
      self.cards[card.name] = card
    agent_info = []
    for ra in self.list_remote_agents():
      agent_info.append(json.dumps(ra))
    self.agents = '\n'.join(agent_info)
    # Create validator agent instance for this host agent
    model_name = self.validator_agent_config['model']
    if model_name.startswith('gemini'):
      model = model_name
    else:
      model = LiteLlm(model=model_name)
    self.validator_agent = LlmAgent(
        name="ValidatorAgent",
        description="Evaluates whether an agent's response properly addresses the user's request. If not, identifies a more appropriate agent from the available list for task reassignment.",
        model=model,
        instruction=self.root_varify_instruction,
        tools=[self.send_task,
               self.list_remote_agents]
    )
    

  def root_varify_instruction(self, context: ReadonlyContext) -> str:
    current_agent = self.check_state(context)
    return f"""
            You are a validator agent responsible for evaluating whether a response from an agent properly addresses the user's request. Your job is to score the response on a 100-point scale based on how well it meets the user's needs, then determine if re-delegation is needed.
            You will be given:

            - The original user request
            - The response from a specific agent
            - The name of the responding agent

            Your tasks:
            1. Analyze whether the response fully and appropriately addresses the user's request.
            
            - Be specific in your reasoning.
            - Consider both the content and intent of the user's request.
            - Evaluate the quality, completeness, relevance, and clarity of the response.
            - Give a score from 0 to 100 based on how well the response meets the request.
            
            2. If the response scores below 80 points:

            - Identify which agent would be more suitable to handle the request.
            - Clearly state the following format:
              ```
              Response is NOT appropriate. Score: <score>. Suggested agent: <agent name>
              ```
            - Use the send_task tool to re-delegate the request to the appropriate agent.
            - Summarize the necessary improvements clearly and pass them along to the reassigned agent.
            - When re-delegating, briefly and clearly instruct the new agent on the specific improvements that need to be made

            3. If the response scores 80 points or above:

            - Return the response as is, including the score in this format:
            - Response is appropriate. Score: <score> <response>
            
          Judging agent suitability:
            - Evaluate if the correct agent has been selected for the task based on the content and intent of the request.
            - If the response is not appropriate for the task, use send_task to assign it to a more suitable agent.
            - If additional improvements are needed, ask the appropriate agent to address only the necessary revisions when re-delegating.

          Constraints:
            - Keep your output structured and concise for easy parsing by the delegator.
            - Do not attempt to solve or modify the user's original request yourself.
            - Use list_remote_agents to view available agents if needed for reassignment.

          Agents: {self.agents}
          Current agent: {current_agent['active_agent']}
"""
    
  def register_agent_card(self, card: AgentCard):
    remote_connection = RemoteAgentConnections(card)
    self.remote_agent_connections[card.name] = remote_connection
    self.cards[card.name] = card
    agent_info = []
    for ra in self.list_remote_agents():
      agent_info.append(json.dumps(ra))
    self.agents = '\n'.join(agent_info)

  def create_agent(self) -> Agent:
    model_name = self.host_agent_config['model']
    if model_name.startswith('gemini'):
      model = model_name
    else:
      model = LiteLlm(model=model_name)
    return Agent(
        model=model,
        name="host_agent",
        instruction=self.root_instruction,
        before_model_callback=self.before_model_callback,
        description=(
            "This agent orchestrates the decomposition of the user request into tasks that can be performed by the child agents."
        ),
        tools=[
            self.list_remote_agents,
            self.send_task,
            agent_tool.AgentTool(agent=self.validator_agent)
        ],
    )

  def root_instruction(self, context: ReadonlyContext) -> str:
    current_agent = self.check_state(context)
    return f"""
            You are the host agent responsible for coordinating user communication across multiple expert agents in a multi-agent system.

            Discovery:
            - You can use `list_remote_agents` to list the available remote agents you can use to delegate the task.

            Execution:
            - For actionable tasks, you can use `create_task` to assign tasks to remote agents to perform. Be sure to include the remote agent name when you respond to the user.

            Your role:
            - Please synthesize the responses from each agent and clearly provide the relevant information so that the next agent can use it.
            - Act as the primary interface with the user.
            - Break down user input into sub-requests (if needed) and delegate to the appropriate agents via the delegator.
            - Use agent_tool.AgentTool(agent=self.validator_agent) to verify responses from agents. If a response fails validation, provide feedback and request revisions from the original agent.
            - Deliver validated responses to the user in a natural, cohesive manner.

            Key responsibilities:
            - Relay agent-generated questions to the user without altering, repeating, or paraphrasing them.
            - Avoid asking the user for information already requested by an agent.
            - Do not ask the user which agent is appropriate — this is handled internally.
            - Reuse existing context to prevent redundant questions.
            - Once all required information is collected, submit the full input to the appropriate agent and deliver the validated result.
            - If the response from an agent does not meet the user's needs or fails validation, you must re-delegate the task to the appropriate agent with specific instructions for improvement.
            - If the user input is unclear or ambiguous, ask clarifying questions before delegating tasks to agents. Avoid making assumptions about the user's intent.
            - Ensure that all delegated tasks are monitored for progress and completion. If needed, follow up with the responsible agent to ensure timely responses.
            - Prioritize responses that are most relevant to the user’s query, ensuring that the task is not only complete but meets the user’s expectations.
            - If an error occurs during task execution (e.g., an agent fails to respond or provide valid information), address the issue immediately and work with the relevant agents to correct the issue.
            - Once a response is delivered to the user, confirm if the user’s needs have been met and ask if further assistance is required.

            Constraints:
            - Do not make assumptions, inferences, or generate new content on your own; if additional information is needed, explicitly request it from the user.
            - Do not think on your own, always rely on self.validator_agent responses.
            - Maintain a clean and structured conversation flow.

            Tools available: list_remote_agents, send_task, agent_tool.AgentTool(agent=self.validator_agent)

      Agents: {self.agents}
      Current agent: {current_agent['active_agent']}
"""

            
  def check_state(self, context: ReadonlyContext):
    state = context.state
    if ('session_id' in state and
        'session_active' in state and
        state['session_active'] and
        'agent' in state):
      return {"active_agent": f'{state["agent"]}'}
    return {"active_agent": "None"}

  def before_model_callback(self, callback_context: CallbackContext, llm_request):
    state = callback_context.state
    if 'session_active' not in state or not state['session_active']:
      if 'session_id' not in state:
        state['session_id'] = str(uuid.uuid4())
      state['session_active'] = True

  def list_remote_agents(self):
    """List the available remote agents you can use to delegate the task."""
    if not self.remote_agent_connections:
      return []

    remote_agent_info = []
    for card in self.cards.values():
      remote_agent_info.append(
          {"name": card.name, "description": card.description}
      )
    return remote_agent_info

  async def send_task(
      self,
      agent_name: str,
      message: str,
      tool_context: ToolContext):
    """Sends a task either streaming (if supported) or non-streaming.

    This will send a message to the remote agent named agent_name.

    Args:
      agent_name: The name of the agent to send the task to.
      message: The message to send to the agent for the task.
      tool_context: The tool context this method runs in.

    Returns:
      A list of response parts from the task.
    """
    if agent_name not in self.remote_agent_connections:
      raise ValueError(f"Agent {agent_name} not found")
    
    state = tool_context.state
    state['agent'] = agent_name
    
    client = self.remote_agent_connections[agent_name]
    if not client:
      raise ValueError(f"Client not available for {agent_name}")
    
    # Generate task ID and session ID
    task_id = state.get('task_id', str(uuid.uuid4()))
    session_id = state.get('session_id', str(uuid.uuid4()))
    
    # Prepare message metadata
    metadata = {
        'conversation_id': session_id,
        'message_id': state.get('input_message_metadata', {}).get('message_id', str(uuid.uuid4()))
    }
    if 'input_message_metadata' in state:
        metadata.update(**state['input_message_metadata'])
    
    # Create task request
    request = TaskSendParams(
        id=task_id,
        sessionId=session_id,
        message=Message(
            role="user",
            parts=[TextPart(text=message)],
            metadata=metadata,
        ),
        acceptedOutputModes=["text", "text/plain"],
        metadata={'conversation_id': session_id},
    )
    
    try:
        # Send task and get response
        # Send the request as a message to the queue (for chat display)
        await task_queue.put({
            "type": "request",
            "request": request,
            "task_id": task_id,
            "session_id": session_id
        })

        # Send task and get response
        task = await client.send_task(request, self.task_callback)

        # Send the response as a message to the queue (for chat display)
        await task_queue.put({
            "type": "response",
            "task": task,
            "task_id": task_id,
            "session_id": session_id
        })
        
        # Update session state
        state['session_active'] = task.status.state not in [
            TaskState.COMPLETED,
            TaskState.CANCELED,
            TaskState.FAILED,
            TaskState.UNKNOWN,
        ]
        
        # Handle task status
        if task.status.state == TaskState.INPUT_REQUIRED:
            tool_context.actions.skip_summarization = True
            tool_context.actions.escalate = True
            return []
        elif task.status.state in [TaskState.CANCELED, TaskState.FAILED]:
            raise ValueError(f"Task {task_id} {task.status.state.lower()}")
        
        # Collect and return response parts
        response = []
        if task.status.message and task.status.message.parts:
            response.extend(task.status.message.parts)
        if task.artifacts:
            for artifact in task.artifacts:
                if artifact.parts:
                    response.extend(artifact.parts)
        return response
        
    except Exception as e:
        print(f"Error in send_task: {e}")
        raise

