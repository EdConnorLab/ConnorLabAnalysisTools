from __future__ import annotations

from collections import OrderedDict

import ast
import pandas as pd

from clat.compile.tstamp.tstamp_field import DatabaseField
from clat.util.connection import Connection


class CachedTaskDatabaseField(DatabaseField):
    """
    A DatabaseField that caches its value in the database so it can be used for analysis without need to refetch data or store in
    serialized intermediate format. This version uses task_id instead of When objects.

    Override get_cached_value and cache_value to change the caching logic.
    """

    def __init__(self, conn: Connection):
        self.conn = conn
        self.name = self.get_name()
        super().__init__(conn, self.get_name())
        self._ensure_cache_table_exists()

    def get_cached_super(self, task_id: str, super_type: type[CachedTaskDatabaseField], *args, **kwargs):
        """
        Get the value of the superclass instance of the specified type, caching it if necessary.
        If the field is not a superclass of this, it may fail if the superclass does not have compatible
        constructor parameters.

        for *args and **kwargs, pass the same arguments as the superclass constructor (excluding conn)
        """
        # Dynamically create an instance of the specified superclass
        super_field = super_type(self.conn, *args, **kwargs)

        # Attempt to retrieve cached value
        cached_value = self._get_cached_value(super_field.get_name(), task_id)
        if cached_value is not None:
            return self.convert_from_string(cached_value)

        # Fetch data using the superclass's get method and cache it
        data = super_field.get(task_id)
        self._cache_value(super_field.get_name(), task_id, data)
        converted_value = self.convert_from_string(self._get_cached_value(super_field.get_name(), task_id))
        return converted_value

    def get_and_cache(self, name: str, task_id: str):
        cached_value = self._get_cached_value(name, task_id)
        if cached_value is not None:
            return self.convert_from_string(cached_value)

        data = self.get(task_id)
        self._cache_value(name, task_id, data)
        # return the cached value rather than raw value to ensure same data-types are returned for all calls
        cached_value = self._get_cached_value(name, task_id)
        return self.convert_from_string(cached_value)

    def convert_from_string(self, cached_value):
        try:
            return ast.literal_eval(cached_value)
        except ValueError:
            return cached_value
        except SyntaxError:
            return cached_value

    def _get_cached_value(self, name: str, task_id: str):
        # Implement the logic to query the TaskFieldCache table
        # to retrieve the cached value, if it exists and is still valid.
        query = "SELECT value FROM TaskFieldCache WHERE name = %s AND task_id = %s;"
        self.conn.execute(query, params=(name, task_id))
        result = self.conn.fetch_all()
        return result[0][0] if result else None

    def _cache_value(self, name: str, task_id: str, value):
        value = str(value)
        # Implement the logic to insert or update the cached value
        # in the TaskFieldCache table.
        query = """
        INSERT INTO TaskFieldCache (name, task_id, value) 
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE value = %s;
        """
        self.conn.execute(query, params=(name, task_id, value, value))

    def _ensure_cache_table_exists(self):
        """Ensures that the TaskFieldCache table exists in the database."""
        # Check if the table exists
        check_table_query = """
        SELECT COUNT(*)
        FROM information_schema.tables
        WHERE table_schema = DATABASE()
        AND table_name = 'TaskFieldCache';
        """
        self.conn.execute(check_table_query)
        result = self.conn.fetch_all()

        # Create the table if it doesn't exist
        if result[0][0] == 0:
            create_table_query = """
            CREATE TABLE `TaskFieldCache` (
              `name` varchar(255) NOT NULL,
              `task_id` varchar(255) NOT NULL,
              `value` longtext,
              PRIMARY KEY (`name`,`task_id`)
            ) ENGINE=InnoDB DEFAULT CHARSET=latin1
            """
            self.conn.execute(create_table_query)

    def get_name(self) -> str:
        raise NotImplementedError("Subclasses must implement get_name")

    def get(self, task_id: str):
        """
        Subclasses should override this method to fetch the actual data.
        """
        raise NotImplementedError("Subclasses must implement get")


class CachedTaskFieldList(list[CachedTaskDatabaseField]):
    def get_df(self):
        df = pd.DataFrame(columns=self.get_names())
        return df

    def get_names(self):
        return [field.get_name() for field in self]

    def to_data(self, task_ids: list[str]) -> pd.DataFrame:
        return self._get_data_from_tasks(task_ids)

    def _get_data_from_tasks(self, task_ids: list[str]) -> pd.DataFrame:
        data = []
        for i, task_id in enumerate(task_ids):
            print(f"working on {i} out of {len(task_ids)}")
            field_values = []
            for field in self:
                try:
                    field_values.append(field.get_and_cache(field.name, task_id))
                except Exception as e:
                    print(f"Error fetching {field.name} for task {task_id}: {e}")
                    field_values.append(None)
            field_values.insert(0, task_id)
            names = self.get_names()
            names.insert(0, "TaskId")
            new_row = OrderedDict(zip(names, field_values))
            data.append(new_row)

        return pd.DataFrame(data)


"""
CREATE TABLE `TaskFieldCache` (
  `name` varchar(255) NOT NULL,
  `task_id` varchar(255) NOT NULL,
  `value` longtext,
  PRIMARY KEY (`name`,`task_id`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1
"""