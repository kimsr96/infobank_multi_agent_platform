from a2a_types import AgentCard, A2ARequest, GetTaskRequest, SendTaskRequest, JSONRPCResponse
from starlette.responses import JSONResponse
from starlette.requests import Request
from sse_starlette.sse import EventSourceResponse
from fastapi.encoders import jsonable_encoder
from server.task_manager import TaskManager
from a2a_types import SendTaskStreamingRequest
from typing import AsyncIterable, Any
from fastapi import FastAPI

class A2AServer:
    def __init__(
        self,
        agent_card: AgentCard,
        task_manager: TaskManager,
        host: str = "localhost",
        port: int = 10000,
    ):
        self.agent_card = agent_card
        self.task_manager = task_manager
        self.host = host
        self.port = port
        self.app = FastAPI()
        self._setup_routes()

    def _setup_routes(self):
        @self.app.get("/")
        async def get_agent_card():
            return self.agent_card.model_dump(exclude_none=True)

        @self.app.post("/")
        async def handle_post_request(request: Request):
            return await self._handle_request(request)

        @self.app.get("/.well-known/agent.json")
        async def get_agent_card_json():
            return self.agent_card.model_dump(exclude_none=True)

        @self.app.post("/task")
        async def create_task(task):
            return await self.task_manager.create_task(task)

        @self.app.get("/task/{task_id}")
        async def get_task(task_id: str):
            return await self.task_manager.get_task(task_id)

        @self.app.post("/task/{task_id}/update")
        async def update_task(task_id: str, update):
            return await self.task_manager.update_task(task_id, update)

    def start(self):
        if self.agent_card is None:
            raise ValueError("agent_card is not defined")

        if self.task_manager is None:
            raise ValueError("task_manager is not defined")

        import uvicorn

        uvicorn.run(self.app, host=self.host, port=self.port)
    
    def _get_agent_card(self, request: Request) -> JSONResponse:
        return JSONResponse(self.agent_card.model_dump(exclude_none=True))
        
    async def _handle_request(self, request: Request):
        body = await request.json()
        json_rpc_request = A2ARequest.validate_python(body)
        
        if isinstance(json_rpc_request, GetTaskRequest):
            result = await self.task_manager.on_get_task(json_rpc_request)
            return self._create_response(result)
        elif isinstance(json_rpc_request, SendTaskRequest):
            result = await self.task_manager.on_send_task(json_rpc_request)
            return self._create_response(result)
        elif isinstance(json_rpc_request, SendTaskStreamingRequest):
            result = await self.task_manager.on_send_task_subscribe(json_rpc_request)
        else:
            raise ValueError(f"Unexpected request type: {type(request)}")
        return self._create_response(result)
    
    def _create_response(self, result: Any) -> JSONResponse | EventSourceResponse:
        if isinstance(result, AsyncIterable):
            async def event_generator(result) -> AsyncIterable[dict[str, str]]:
                async for item in result:
                    yield {"data": item.model_dump_json(exclude_none=True)}
            return EventSourceResponse(event_generator(result))
        elif isinstance(result, JSONRPCResponse):
            return JSONResponse(content=jsonable_encoder(result.model_dump(exclude_none=True)))
        else:
            raise ValueError("Invalid response type")
