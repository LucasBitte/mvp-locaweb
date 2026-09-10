from cloud.compare import fingerprint


class Connection:
    class dialect:
        class identifier_preparer:
            @staticmethod
            def quote(name):
                return '"' + name.replace('"', '""') + '"'

    def __init__(self, rows):
        self.rows = rows

    def execute(self, query):
        return [(row,) for row in self.rows]


def test_checksum_independe_da_ordem_e_preserva_duplicatas():
    def digest(rows):
        return fingerprint(Connection(rows), 'dw', 'fct_incidentes')
    assert digest(['a', 'b']) == digest(['b', 'a'])
    assert digest(['a', 'b']) != digest(['a', 'b', 'b'])
    assert digest(['ab', 'c']) != digest(['a', 'bc'])
