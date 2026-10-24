"""Deterministic task scheduler for main-thread polling and deferred cleanup tests."""
from types import SimpleNamespace

class TaskDouble(SimpleNamespace):
    __hash__=object.__hash__
    __eq__=object.__eq__

class TaskManagerDouble:
    def __init__(self): self.tasks=[]
    def _add(self,function,name,deferred):
        task=TaskDouble(function=function,name=name,deferred=deferred,done='done',cont='cont')
        self.tasks.append(task)
        return task
    def add(self,function,name):return self._add(function,name,False)
    def doMethodLater(self,delay,function,name):return self._add(function,name,True)
    def remove(self,task):
        self.tasks=[item for item in self.tasks if item is not task and item.name!=task]
    def tick(self,*,deferred_only=False):
        for task in self.tasks[:]:
            if deferred_only and not task.deferred:continue
            if task in self.tasks and task.function(task)==task.done:self.remove(task)
