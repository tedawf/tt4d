class ScalarResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows

    def first(self):
        if self._rows:
            return self._rows[0]
        return None


class ExecuteResult:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return ScalarResult(self._rows)


class FakeDB:
    def __init__(self, execute_rows=None, get_row=None):
        self._execute_rows = list(execute_rows or [])
        self._get_row = get_row

    def execute(self, _query):
        rows = self._execute_rows.pop(0) if self._execute_rows else []
        return ExecuteResult(rows)

    def get(self, _model, _draw_number):
        return self._get_row
