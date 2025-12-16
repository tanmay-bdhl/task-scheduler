from pydantic import BaseModel, Field
from typing import List

class TaskCreateRequest(BaseModel):
    id: str = Field(..., example="task-A")
    type: str = Field(..., example="data_processing")
    duration_ms: int = Field(..., gt=0)
    dependencies: List[str] = Field(default_factory=list)


class TaskCreateResponse(BaseModel):
    id: str
    status: str
    
class TaskResponse(BaseModel):
    id: str
    type: str
    duration_ms: int
    status: str

class TaskListResponse(BaseModel):
    tasks: List[TaskResponse]