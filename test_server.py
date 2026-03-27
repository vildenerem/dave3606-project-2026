import json
import unittest
from unittest.mock import mock_open, patch

from server import get_api_set_json, get_sets_html


class MockDatabase:
    """
    A test double for the Database class. Checks that the query it receives
    matches the expected query, returns canned rows, and records whether
    close() was called.
    """

    def __init__(self, expected_query, rows):
        self.expected_query = expected_query
        self.rows = rows
        self.was_closed = False

    def execute_and_fetch_all(self, query):
        assert query == self.expected_query, (
            f"Wrong SQL query.\n  Expected: {self.expected_query!r}\n  Got:      {query!r}"
        )
        return self.rows

    def close(self):
        self.was_closed = True


# ---------------------------------------------------------------------------
# Tests for get_sets_html
# ---------------------------------------------------------------------------

SETS_QUERY = "select id, name from lego_set order by id"
FAKE_SETS_TEMPLATE = "<table>{ROWS}</table>"


class TestGetSetsHtml(unittest.TestCase):
    def _call(self, rows):
        db = MockDatabase(expected_query=SETS_QUERY, rows=rows)
        with patch("builtins.open", mock_open(read_data=FAKE_SETS_TEMPLATE)):
            result = get_sets_html(db)
        return result, db

    def test_each_set_appears_as_a_table_row(self):
        result, _ = self._call([
            ("10497", "Galaxy Explorer"),
            ("75192", "Millennium Falcon"),
        ])

        self.assertIn('<a href="/set?id=10497">10497</a>', result)
        self.assertIn("Galaxy Explorer", result)
        self.assertIn('<a href="/set?id=75192">75192</a>', result)
        self.assertIn("Millennium Falcon", result)

    def test_rows_are_inserted_into_template(self):
        result, _ = self._call([("10497", "Galaxy Explorer")])

        # The {ROWS} placeholder must have been replaced – the literal
        # string should no longer appear in the output.
        self.assertNotIn("{ROWS}", result)
        # The wrapping table tags from the fake template must still be there.
        self.assertIn("<table>", result)
        self.assertIn("</table>", result)

    def test_empty_result_produces_empty_table(self):
        result, _ = self._call([])

        self.assertNotIn("{ROWS}", result)
        self.assertNotIn("<tr>", result)

    def test_html_special_characters_in_id_and_name_are_escaped(self):
        result, _ = self._call([('<script>alert(1)</script>', '<b>Evil</b>')])

        # Raw tags must not appear unescaped.
        self.assertNotIn("<script>", result)
        self.assertNotIn("<b>Evil</b>", result)
        # Escaped versions must be present.
        self.assertIn("&lt;script&gt;", result)
        self.assertIn("&lt;b&gt;Evil&lt;/b&gt;", result)

    def test_database_is_closed(self):
        _, db = self._call([("10497", "Galaxy Explorer")])

        self.assertTrue(db.was_closed, "Database.close() should have been called")


# ---------------------------------------------------------------------------
# Tests for get_api_set_json
# ---------------------------------------------------------------------------

# get_api_set_json currently doesn't execute any SQL, so the mock uses an
# empty query / empty rows.  The query assertion still fires if the
# implementation starts issuing unexpected queries.
API_SET_QUERY = ""


class TestGetApiSetJson(unittest.TestCase):
    def _call(self, set_id, rows=None):
        db = MockDatabase(expected_query=API_SET_QUERY, rows=rows or [])
        result = get_api_set_json(set_id, db)
        return result, db

    def test_returns_valid_json(self):
        result, _ = self._call("10497")

        # Must not raise.
        parsed = json.loads(result)
        self.assertIsInstance(parsed, dict)

    def test_set_id_is_included_in_response(self):
        result, _ = self._call("10497")

        parsed = json.loads(result)
        self.assertEqual(parsed["set_id"], "10497")

    def test_none_set_id_is_handled(self):
        result, _ = self._call(None)

        parsed = json.loads(result)
        self.assertIsNone(parsed["set_id"])

    def test_database_is_closed(self):
        _, db = self._call("10497")

        self.assertTrue(db.was_closed, "Database.close() should have been called")


if __name__ == "__main__":
    unittest.main()