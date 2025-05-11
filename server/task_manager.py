from abc import ABC, abstractmethod
from asyncio import Lock
from typing import Dict, Union, AsyncIterable
from a2a_types import (GetTaskRequest, SendTaskRequest, GetTaskResponse, SendTaskResponse,
        Task, TaskSendParams, TaskState, TaskStatus, TaskQueryParams, TaskNotFoundError)
from a2a_types import (SendTaskStreamingRequest, SendTaskStreamingResponse, JSONRPCResponse)

class TaskManager(ABC):
    @abstractmethod
    async def on_get_task(self, request: GetTaskRequest) -> GetTaskResponse:
        pass
    
    @abstractmethod
    async def on_send_task(self, request: SendTaskRequest) -> SendTaskResponse:
        pass
    
    @abstractmethod
    async def on_send_task_subscribe(
        self, request: SendTaskStreamingRequest
    ) -> Union[AsyncIterable[SendTaskStreamingResponse], JSONRPCResponse]:
        pass
    
    # @abstractmethod
    # async def on_cancel_task(self, request: CancelTaskRequest) -> CancelTaskResponse:
    #     pass


    # @abstractmethod
    # async def on_set_task_push_notification(
    #     self, request: SetTaskPushNotificationRequest
    # ) -> SetTaskPushNotificationResponse:
    #     pass

    # @abstractmethod
    # async def on_get_task_push_notification(
    #     self, request: GetTaskPushNotificationRequest
    # ) -> GetTaskPushNotificationResponse:
    #     pass

    # @abstractmethod
    # async def on_resubscribe_to_task(
    #     self, request: TaskResubscriptionRequest
    # ) -> Union[AsyncIterable[SendTaskResponse], JSONRPCResponse]:
    #     pass
    
class InMemoryTaskManager(TaskManager):
    
    def __init__(self):
        self.tasks: Dict[str, Task] = {}   # 🗃️ Dictionary where key = task ID, value = Task object
        self.lock = Lock()  
    
    @abstractmethod
    async def on_send_task(self, request: SendTaskRequest) -> SendTaskResponse:
        pass
    
    async def on_get_task(self, request: GetTaskRequest) -> GetTaskResponse:
        task_query_params: TaskQueryParams = request.params

        async with self.lock:
            task = self.tasks.get(task_query_params.id)
            if task is None:
                return GetTaskResponse(id=request.id, error=TaskNotFoundError())

            task_result = self.append_task_history(
                task, task_query_params.historyLength
            )

        return GetTaskResponse(id=request.id, result=task_result)
    
    async def upsert_task(self, params: TaskSendParams) -> Task:
        async with self.lock:
            task = self.tasks.get(params.id)  # Try to find an existing task with this ID
        if task is None:
            # If task doesn't exist, create it with a "submitted" status
            task = Task(
                id=params.id,
                status=TaskStatus(state=TaskState.SUBMITTED),
                history=[params.message]
            )
            self.tasks[params.id] = task
        else:
            # If task exists, add the new message to its history
            task.history.append(params.message)

        return task