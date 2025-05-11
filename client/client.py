import httpx
import json
from typing import Any, AsyncIterable
from a2a_types import (
    AgentCard, SendTaskRequest, SendTaskResponse,
    A2AClientHTTPError, A2AClientJSONError,
    GetTaskRequest, GetTaskResponse,
    JSONRPCRequest, JSONRPCResponse, SendTaskStreamingResponse,
    SendTaskStreamingRequest
)
from httpx_sse import connect_sse, SSEError

import logging
logger = logging.getLogger(__name__)

class A2AClient:
    def __init__(self, agent_card: AgentCard = None, url: str = None):
        if agent_card:
            self.url = agent_card.url
        elif url:
            self.url = url
        else:
            raise ValueError("Must provide either agent_card or url")
    
    async def send_task(self, payload: dict[str, Any]) -> SendTaskResponse:
        request = SendTaskRequest(params=payload)
        return SendTaskResponse(**await self._send_request(request))
    
    async def send_task_streaming(
        self, payload: dict[str, Any]
        ) -> AsyncIterable[SendTaskStreamingResponse]:
        
        """
        Send a task and receive streaming updates using SSE.
        Args:
            payload: The task payload
        Returns:
            An async iterable of SendTaskStreamingResponse objects
        """
        request = SendTaskStreamingRequest(params=payload)
        
        with httpx.Client(timeout=None) as client:
                with connect_sse(
                    client, "POST", self.url, json=request.model_dump()
                ) as event_source:
                    try:
                        for sse in event_source.iter_sse():
                            yield SendTaskStreamingResponse(**json.loads(sse.data))
                    except SSEError as e:
                        # Fallback for non-streaming responses
                        if "application/json" in str(e):
                            logger.warning("Server returned JSON instead of SSE. Falling back to non-streaming.")
                            response = await self.send_task(payload)
                            yield SendTaskStreamingResponse(
                                id=response.id,
                                result={
                                    "is_task_complete": True,
                                    "require_user_input": False,
                                    "content": response.result.status.message.parts[0].text if response.result and response.result.status and response.result.status.message and response.result.status.message.parts else "",
                                }
                            )
    
    async def _send_request(self, request: JSONRPCRequest) -> dict[str, Any]:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self.url, json=request.model_dump(), timeout=60
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                raise A2AClientHTTPError(e.response.status_code, str(e)) from e
            except json.JSONDecodeError as e:
                raise A2AClientJSONError(str(e)) from e
            
    async def get_task(self, payload: dict[str, Any]) -> GetTaskResponse:
        request = GetTaskRequest(params=payload)
        return GetTaskResponse(**await self._send_request(request))
