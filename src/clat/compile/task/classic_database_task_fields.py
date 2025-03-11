from clat.compile.task.task_field import TaskField
from clat.util.connection import Connection
from clat.compile.task.cached_task_fields import CachedTaskDatabaseField


class TaskIdField(CachedTaskDatabaseField):
    def __init__(self, conn: Connection):
        super().__init__(conn)

    def get(self, task_id: int) -> int:
        return task_id

    def get_name(self) -> str:
        return "TaskId"


class StimSpecIdField(CachedTaskDatabaseField):
    def __init__(self, conn: Connection):
        super().__init__(conn)

    def get_name(self) -> str:
        return "TaskId"

    def get(self, task_id: int) -> int:
        # Execute the query to get the StimSpecId based on task_id
        query = "SELECT stim_id FROM TaskToDo WHERE task_id = %s"
        params = (task_id,)
        self.conn.execute(query, params)
        result = self.conn.fetch_one()
        stim_spec_id = result[0] if result else None
        return int(stim_spec_id) if stim_spec_id is not None else None


class StimSpecField(StimSpecIdField):
    def __init__(self, conn: Connection):
        super().__init__(conn)

    def get_name(self) -> str:
        return "StimSpecId"

    def get(self, task_id: int) -> str:
        # Use get_cached_super to leverage the cached StimSpecId
        stim_id = self.get_cached_super(task_id, StimSpecIdField)
        if stim_id is None:
            return None

        # Execute the query to get the StimSpec based on stim_id
        query = "SELECT spec FROM StimSpec WHERE id = %s"
        params = (stim_id,)
        self.conn.execute(query, params)
        result = self.conn.fetch_one()
        return result[0] if result else None


class StimSpecDataField(StimSpecIdField):
    def __init__(self, conn: Connection):
        super().__init__(conn)

    def get_name(self) -> str:
        return "StimSpecData"

    def get(self, task_id: int):
        # Use get_cached_super to leverage the cached StimSpecId
        stim_id = self.get_cached_super(task_id, StimSpecIdField)
        if stim_id is None:
            return None

        # Execute the query to get the StimSpecData based on stim_id
        query = "SELECT data FROM StimSpec WHERE id = %s"
        params = (stim_id,)
        self.conn.execute(query, params)
        result = self.conn.fetch_one()
        return result[0] if result else None

