import importlib
from datetime import timedelta
from typing import Union

from c4_sign.base_task import OptimScreenTask, ScreenTask
from c4_sign.lib.canvas import Canvas
from c4_sign.loading_manager import LoadingManager


class ScreenManager:
    def __init__(self):
        self.tasks = []
        self.current_task = None
        self.index = 0

    @property
    def current_tasks(self) -> list[ScreenTask]:
        return self.tasks

    def update_tasks(self, loading_manager: Union[None, LoadingManager] = None):
        # import all files in screen_tasks
        mod = importlib.import_module("c4_sign.screen_tasks")
        for obj in mod.__all__:
            obj = importlib.import_module(f"c4_sign.screen_tasks.{obj}")
            for name, obj in obj.__dict__.items():
                if (
                    isinstance(obj, type)
                    and issubclass(obj, ScreenTask)
                    and obj not in (ScreenTask, OptimScreenTask)
                    and obj.ignore is False
                ):
                    if loading_manager:
                        with loading_manager(obj.__name__):
                            self.tasks.append(obj())
                    else:
                        self.tasks.append(obj())

    def override_current_task(self, task: Union[str, ScreenTask]):
        # if task is a string, find the task by name
        if isinstance(task, str):
            for t in self.tasks:
                if t.__class__.__name__ == task:
                    task = t
                    break
            else:
                # task not found!
                print(f"Task {task} not found!")
                return
        if self.current_task:
            self.current_task.teardown(True)
        self.current_task = task
        self.current_task.prepare()
        self.index = -1

    def draw(self, canvas: Canvas, delta_time: timedelta):
        if not self.current_task:
            if self.index >= len(self.current_tasks):
                self.index = 0
            self.current_task = self.current_tasks[self.index]
            if not self.current_task.prepare():
                # uh... we don't want to do anything!
                # so let's just skip this task!
                self.current_task = None
                self.index += 1
                if self.index >= len(self.current_tasks):
                    self.index = 0
                return self.draw(canvas, delta_time)
        if self.current_task.draw(canvas, delta_time):
            self.current_task.teardown()
            self.current_task = None
            self.index += 1
            return True
        return False

    def get_lcd_text(self):
        if self.current_task:
            return self.current_task.get_lcd_text()
        else:
            return " " * 32
