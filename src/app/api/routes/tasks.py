from fastapi import APIRouter, HTTPException, status

from src.app.schemas.voice import Task, TaskCreate, TaskReplace, TaskUpdate

router = APIRouter(prefix="/tasks", tags=["tasks"])
tasks: list[Task] = []
next_task_id = 1


@router.get("", response_model=list[Task])
def get_tasks() -> list[Task]:
    return tasks


@router.post("", response_model=Task, status_code=status.HTTP_201_CREATED)
def create_task(payload: TaskCreate) -> Task:
    global next_task_id
    task = Task(id=next_task_id, title=payload.title, done=payload.done)
    next_task_id += 1
    tasks.append(task)
    return task


@router.put("/{task_id}", response_model=Task)
def replace_task(
    task_id: int,
    payload: TaskReplace,
) -> Task:
    index = _get_task_index(task_id)
    task = Task(id=task_id, title=payload.title, done=payload.done)
    tasks[index] = task
    return task


@router.patch("/{task_id}", response_model=Task)
def update_task(
    task_id: int,
    payload: TaskUpdate,
) -> Task:
    index = _get_task_index(task_id)
    current_task = tasks[index]
    updated = current_task.model_copy(
        update=payload.model_dump(exclude_unset=True)
    )
    tasks[index] = updated
    return updated


@router.delete("/{task_id}")
def delete_task(task_id: int) -> dict[str, str | int]:
    index = _get_task_index(task_id)
    del tasks[index]
    return {"message": "Task deleted successfully", "task_id": task_id}


def _get_task_index(task_id: int) -> int:
    for index, task in enumerate(tasks):
        if task.id == task_id:
            return index
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Task with id {task_id} was not found.",
    )
