from uuid import uuid4
from pydantic import BaseModel, Field, model_validator, field_serializer, TypeAdapter
from typing import List, Literal, Any, Annotated, Union, Dict, Optional, Self
from datetime import datetime
from enum import Enum

class FileContent(BaseModel):
    name: str | None = None
    mimeType: str | None = None
    bytes: str | None = None
    uri: str | None = None

    @model_validator(mode="after")
    def check_content(self) -> Self:
        if not (self.bytes or self.uri):
            raise ValueError("Either 'bytes' or 'uri' must be present in the file data")
        if self.bytes and self.uri:
            raise ValueError(
                "Only one of 'bytes' or 'uri' can be present in the file data"
            )
        return self
    
class TextPart(BaseModel):
    type: Literal["text"] = "text" 
    text: str 
    
class DataPart(BaseModel):
    type: Literal["data"] = "data"
    data: dict[str, Any]
    metadata: dict[str, Any] | None = None

class FilePart(BaseModel):
    type: Literal["file"] = "file"
    file: FileContent
    metadata: dict[str, Any] | None = None

Part = Union[TextPart, DataPart, FilePart]

class A2AClientHTTPError(Exception):
    """Raised when an HTTP request fails (e.g., bad server response)"""
    pass

class A2AClientJSONError(Exception):
    """Raised when the response is not valid JSON"""
    pass
        
class Message(BaseModel):
    role: str
    parts: List[Part]
    metadata: Optional[Dict[str, Any]] = None

class TaskIdParams(BaseModel):
    id: str

class TaskSendParams(BaseModel):
    id: str
    sessionId: str = Field(default_factory=lambda: uuid4().hex)
    message: Message
    historyLength: int | None = None
    metadata: dict[str, Any] | None = None

class TaskQueryParams(TaskIdParams):
    historyLength: int | None = None

class TaskState(str, Enum):
    SUBMITTED = "submitted"
    WORKING = "working"
    INPUT_REQUIRED = "input-required"
    COMPLETED = "completed"
    CANCELED = "canceled"
    FAILED = "failed"
    UNKNOWN = "unknown"

class TaskStatus(BaseModel):
    state: str
    message: Message | None = None
    timestamp: datetime = Field(default_factory=datetime.now)
    
    @field_serializer("timestamp")
    def serialize_dt(self, dt: datetime, _info):
        return dt.isoformat()

class Artifact(BaseModel):
    name: str | None = None
    description: str | None = None
    parts: List[Part]
    metadata: dict[str, Any] | None = None
    index: int = 0
    append: bool | None = None
    lastChunk: bool | None = None

class Task(BaseModel):
    id: str
    sessionId: str | None = None
    status: TaskStatus
    artifacts: List[Artifact] | None = None
    history: List[Message] | None = None
    metadata: dict[str, Any] | None = None

class AgentCapabilities(BaseModel):
    streaming: bool = False
    pushNotifications: bool = False
    stateTransitionHistory: bool = False

class AgentSkill(BaseModel):
    id: str
    name: str
    description: str | None = None
    tags: List[str] | None = None
    examples: List[str] | None = None
    inputModes: List[str] | None = None
    outputModes: List[str] | None = None

class AgentCard(BaseModel):
    name: str
    description: str | None = None    
    url: str
    version: str
    capabilities: AgentCapabilities
    skills: List[AgentSkill]

class JSONRPCMessage(BaseModel):
    jsonrpc: Literal["2.0"] = "2.0"
    id: int | str | None = Field(default_factory=lambda: uuid4().hex)
    
class JSONRPCError(BaseModel):
    code: int
    message: str
    data: Any | None = None

class JSONRPCRequest(JSONRPCMessage):
    method: str
    params: Dict[str, Any] = {}

class JSONRPCResponse(JSONRPCMessage):
    result: Any | None = None
    error: JSONRPCError | None = None

class A2ARequest(JSONRPCRequest):
    pass

class GetTaskRequest(A2ARequest):
    method: Literal["tasks/get"] = "tasks/get"
    params: TaskQueryParams
    
class SendTaskRequest(A2ARequest):
    method: Literal["tasks/send"] = "tasks/send"
    params: TaskSendParams

class SendTaskResponse(JSONRPCResponse):
    result: Task | None = None
    
class GetTaskResponse(JSONRPCResponse):
    result: Task | None = None

class TaskNotFoundError(JSONRPCError):
    code: int = -32001
    message: str = "Task not found"
    data: None = None

########################################################
#                   Streaming                          #
########################################################

class Artifact(BaseModel):
    name: str | None = None
    description: str | None = None
    parts: List[Part]
    metadata: dict[str, Any] | None = None
    index: int = 0
    append: bool | None = None
    lastChunk: bool | None = None
    
class TaskStatusUpdateEvent(BaseModel):
    id: str
    status: TaskStatus
    final: bool = False
    metadata: dict[str, Any] | None = None
    
class TaskArtifactUpdateEvent(BaseModel):
    id: str
    artifact: Artifact    
    metadata: dict[str, Any] | None = None

class SendTaskStreamingRequest(JSONRPCRequest):
    method: Literal["tasks/sendSubscribe"] = "tasks/sendSubscribe"
    params: TaskSendParams

class SendTaskStreamingResponse(JSONRPCResponse):
    result: TaskStatusUpdateEvent | TaskArtifactUpdateEvent | None = None

A2ARequest = TypeAdapter(
    Annotated[
        Union[GetTaskRequest, SendTaskRequest, SendTaskStreamingRequest],
        Field(discriminator="method")
    ]
)

########################################################
#                   Service Types                      #
#`#######################################################

class Conversation(BaseModel):
  conversation_id: str
  is_active: bool
  name: str = ''
  task_ids: list[str] = Field(default_factory=list)
  messages: list[Message] = Field(default_factory=list)

class Event(BaseModel):
  id: str
  actor: str = ""
  content: Message
  timestamp: float

class FileContent(BaseModel):
    name: str | None = None
    mimeType: str | None = None
    bytes: str | None = None
    uri: str | None = None

    @model_validator(mode="after")
    def check_content(self) -> Self:
        if not (self.bytes or self.uri):
            raise ValueError("Either 'bytes' or 'uri' must be present in the file data")
        if self.bytes and self.uri:
            raise ValueError(
                "Only one of 'bytes' or 'uri' can be present in the file data"
            )
        return self
    
class FilePart(BaseModel):
    type: Literal["file"] = "file"
    file: FileContent
    metadata: dict[str, Any] | None = None

    
