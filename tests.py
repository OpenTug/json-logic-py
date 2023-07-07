"""
Tests for jsonLogic.
"""
import json
import unittest

from urllib.request import urlopen
from json_logic import jsonLogic


class JSONLogicTest(unittest.TestCase):
    """
    The tests here come from 'Supported operations' page on jsonlogic.com:
    http://jsonlogic.com/operations.html
    """

    def test_var(self):
        """Retrieve data from the provided data object."""
        output, equation = jsonLogic({"var": ["a"]}, {"a": 1, "b": 2})
        self.assertEqual(output, 1)
        self.assertEqual(equation, {"var": ["a"]})

        # If you like, we support syntactic sugar to skip the array around
        # single values.
        output, equation = jsonLogic({"var": "a"}, {"a": 1, "b": 2})
        self.assertEqual(output, 1)
        self.assertEqual(equation, {"var": ["a"]})

        # You can supply a default, as the second argument, for values that
        # might be missing in the data object.
        output, equation = jsonLogic({"var": ["z", 26]}, {"a": 1, "b": 2})
        self.assertEqual(output, 26)
        self.assertEqual(equation, {"var": ["z", 26]})

        # The key passed to var can use dot-notation to get
        # the property of a property (to any depth you need):
        output, equation = jsonLogic(
            {"var": "champ.name"},
            {
                "champ": {"name": "Fezzig", "height": 223},
                "challenger": {"name": "Dread Pirate Roberts", "height": 183},
            },
        )
        self.assertEqual(output, "Fezzig")
        self.assertEqual(equation, {"var": ["champ.name"]})

        # You can also use the var operator to access an array
        # by numeric index:
        output, equation = jsonLogic({"var": 1}, ["apple", "banana", "carrot"])
        self.assertEqual(output, "banana")
        self.assertEqual(equation, {"var": [1]})

        # Here's a complex rule that mixes literals and data. The pie isn't
        # ready to eat unless it's cooler than 110 degrees, and filled
        # with apples.
        output, equation = jsonLogic(
            {"and": [{"<": [{"var": "temp"}, 110]}, {"==": [{"var": "pie.filling"}, "apple"]}]},
            {"temp": 100, "pie": {"filling": "apple"}},
        )
        self.assertTrue(output)
        self.assertEqual(
            equation,
            {
                "and": [
                    {"<": [{"var": ["temp"]}, 110]},
                    {"==": [{"var": ["pie.filling"]}, "apple"]},
                ]
            },
        )

    def test_missing(self):
        """
        Takes an array of data keys to search for (same format as var).
        Returns an array of any keys that are missing from the data object,
        or an empty array.
        """
        output, equation = jsonLogic({"missing": ["a", "b"]}, {"a": "apple", "c": "carrot"})
        self.assertEqual(output, ["b"])
        self.assertEqual(equation, {"missing": ["a", "b"]})

        output, equation = jsonLogic({"missing": ["a", "b"]}, {"a": "apple", "b": "banana"})
        self.assertEqual(output, [])
        self.assertEqual(equation, {"missing": ["a", "b"]})

        # Note, in JsonLogic, empty arrays are falsy. So you can use missing
        # with if like:
        output, equation = jsonLogic(
            {"if": [{"missing": ["a", "b"]}, "Not enough fruit", "OK to proceed"]},
            {"a": "apple", "b": "banana"},
        )
        self.assertEqual(output, "OK to proceed")
        self.assertEqual(equation, "OK to proceed")

    def test_missing_some(self):
        """
        Takes a minimum number of data keys that are required, and an array
        of keys to search for (same format as var or missing). Returns
        an empty array if the minimum is met, or an array of the missing
        keys otherwise.
        """
        output, equation = jsonLogic({"missing_some": [1, ["a", "b", "c"]]}, {"a": "apple"})
        self.assertEqual(output, [])
        self.assertEqual(equation, {"missing_some": [1, ["a", "b", "c"]]})

        output, equation = jsonLogic({"missing_some": [2, ["a", "b", "c"]]}, {"a": "apple"})
        self.assertEqual(output, ["b", "c"])
        self.assertEqual(equation, {"missing_some": [2, ["a", "b", "c"]]})

        # This is useful if you're using missing to track required fields,
        # but occasionally need to require N of M fields.
        output, equation = jsonLogic(
            {
                "if": [
                    {
                        "merge": [
                            {"missing": ["first_name", "last_name"]},
                            {"missing_some": [1, ["cell_phone", "home_phone"]]},
                        ]
                    },
                    "We require first name, last name, and one phone number.",
                    "OK to proceed",
                ]
            },
            {"first_name": "Bruce", "last_name": "Wayne"},
        )
        self.assertEqual(output, "We require first name, last name, and one phone number.")
        self.assertEqual(equation, "We require first name, last name, and one phone number.")

    def test_if(self):
        """
        The if statement typically takes 3 arguments: a condition (if),
        what to do if it's true (then), and what to do if it's false (else).
        """
        output, equation = jsonLogic({"if": [True, "yes", "no"]})
        self.assertEqual(output, "yes")
        self.assertEqual(equation, "yes")

        output, equation = jsonLogic({"if": [False, "yes", "no"]})
        self.assertEqual(output, "no")
        self.assertEqual(equation, "no")

        # If can also take more than 3 arguments, and will pair up arguments
        # like if/then elseif/then elseif/then else. Like:

        output, equation = jsonLogic(
            {
                "if": [
                    {"<": [{"var": "temp"}, 0]},
                    "freezing",
                    {"<": [{"var": "temp"}, 100]},
                    "liquid",
                    "gas",
                ]
            },
            {"temp": 200},
        )
        self.assertEqual(output, "gas")
        self.assertEqual(equation, "gas")

    def test_equality(self):
        """Tests equality, with type coercion. Requires two arguments."""
        output, equation = jsonLogic({"==": [1, 1]})
        self.assertTrue(output)
        self.assertEqual(equation, {"==": [1, 1]})

        output, equation = jsonLogic({"==": [1, "1"]})
        self.assertTrue(output)
        self.assertEqual(equation, {"==": [1, "1"]})

        output, equation = jsonLogic({"==": [0, False]})
        self.assertTrue(output)
        self.assertEqual(equation, {"==": [0, False]})

    def test_stricy_equality(self):
        """Tests strict equality. Requires two arguments."""
        output, equation = jsonLogic({"===": [1, 1]})
        self.assertTrue(output)
        self.assertEqual(equation, {"===": [1, 1]})

        output, equation = jsonLogic({"===": [1, "1"]})
        self.assertFalse(output)
        self.assertEqual(equation, {"===": [1, "1"]})

    def test_nonequality(self):
        """Tests not-equal, with type coercion."""
        output, equation = jsonLogic({"!=": [1, 2]})
        self.assertTrue(output)
        self.assertEqual(equation, {"!=": [1, 2]})

        output, equation = jsonLogic({"!=": [1, "1"]})
        self.assertFalse(output)
        self.assertEqual(equation, {"!=": [1, "1"]})

    def test_strict_nonequality(self):
        """Tests not-equal, with type coercion."""
        output, equation = jsonLogic({"!==": [1, 2]})
        self.assertTrue(output)
        self.assertEqual(equation, {"!==": [1, 2]})

        output, equation = jsonLogic({"!==": [1, "1"]})
        self.assertTrue(output)
        self.assertEqual(equation, {"!==": [1, "1"]})

    def test_not(self):
        """Logical negation ("not"). Takes just one argument."""
        output, equation = jsonLogic({"!": [True]})
        self.assertFalse(output)
        self.assertEqual(equation, {"!": [True]})

        # Note: unary operators can also take a single, non array argument:
        output, equation = jsonLogic({"!": True})
        self.assertFalse(output)
        self.assertEqual(equation, {"!": [True]})

    def test_or(self):
        """
        'or' can be used for simple boolean tests, with 1 or more arguments.
        """
        output, equation = jsonLogic({"or": [True, False]})
        self.assertTrue(output)
        self.assertEqual(equation, {"or": [True, False]})

        # At a more sophisticated level, or returns the first truthy argument,
        # or the last argument.
        output, equation = jsonLogic({"or": [False, True]})
        self.assertTrue(output)
        self.assertEqual(equation, {"or": [False, True]})

        output, equation = jsonLogic({"or": [False, "apple"]})
        self.assertEqual(output, "apple")
        self.assertEqual(equation, {"or": [False, "apple"]})

        output, equation = jsonLogic({"or": [False, None, "apple"]})
        self.assertEqual(output, "apple")
        self.assertEqual(equation, {"or": [False, None, "apple"]})

    def test_and(self):
        """
        'and' can be used for simple boolean tests, with 1 or more arguments.
        """
        output, equation = jsonLogic({"and": [True, True]})
        self.assertTrue(output)
        self.assertEqual(equation, {"and": [True, True]})

        output, equation = jsonLogic({"and": [True, True, True, False]})
        self.assertFalse(output)
        self.assertEqual(equation, {"and": [True, True, True, False]})

        # At a more sophisticated level, and returns the first falsy argument,
        # or the last argument.
        output, equation = jsonLogic({"and": [True, "apple", False]})
        self.assertFalse(output)
        self.assertEqual(equation, {"and": [True, "apple", False]})

        output, equation = jsonLogic({"and": [True, "apple", 3.14]})
        self.assertEqual(output, 3.14)
        self.assertEqual(equation, {"and": [True, "apple", 3.14]})

    def test_cmp(self):
        """Arithmetic comparison functions."""
        # Greater than:
        output, equation = jsonLogic({">": [2, 1]})
        self.assertTrue(output)
        self.assertEqual(equation, {">": [2, 1]})

        # Greater than or equal to:
        output, equation = jsonLogic({">=": [1, 1]})
        self.assertTrue(output)
        self.assertEqual(equation, {">=": [1, 1]})

        # Less than:
        output, equation = jsonLogic({"<": [1, 2]})
        self.assertTrue(output)
        self.assertEqual(equation, {"<": [1, 2]})

        # Less than or equal to:
        output, equation = jsonLogic({"<=": [1, 1]})
        self.assertTrue(output)
        self.assertEqual(equation, {"<=": [1, 1]})

    def test_between(self):
        """
        You can use a special case of < and <= to test that one value
        is between two others.
        """
        # Between exclusive:
        output, equation = jsonLogic({"<": [1, 2, 3]})
        self.assertTrue(output)
        self.assertEqual(equation, {"<": [1, 2, 3]})

        output, equation = jsonLogic({"<": [1, 1, 3]})
        self.assertFalse(output)
        self.assertEqual(equation, {"<": [1, 1, 3]})

        output, equation = jsonLogic({"<": [1, 4, 3]})
        self.assertFalse(output)
        self.assertEqual(equation, {"<": [1, 4, 3]})

        # Between inclusive:
        output, equation = jsonLogic({"<=": [1, 2, 3]})
        self.assertTrue(output)
        self.assertEqual(equation, {"<=": [1, 2, 3]})

        output, equation = jsonLogic({"<=": [1, 1, 3]})
        self.assertTrue(output)
        self.assertEqual(equation, {"<=": [1, 1, 3]})

        output, equation = jsonLogic({"<=": [1, 4, 3]})
        self.assertFalse(output)
        self.assertEqual(equation, {"<=": [1, 4, 3]})

        # This is most useful with data:
        output, equation = jsonLogic({"<": [0, {"var": "temp"}, 100]}, {"temp": 37})
        self.assertTrue(output)
        self.assertEqual(equation, {"<": [0, {"var": ["temp"]}, 100]})

    def test_max_min(self):
        """Return the maximum or minimum from a list of values."""
        output, equation = jsonLogic({"max": [1, 2, 3]})
        self.assertEqual(output, 3)
        self.assertEqual(equation, {"max": [1, 2, 3]})
        output, equation = jsonLogic({"min": [1, 2, 3]})
        self.assertEqual(output, 1)
        self.assertEqual(equation, {"min": [1, 2, 3]})

    def test_arithmetic(self):
        """Arithmetic operators."""
        output, equation = jsonLogic({"+": [1, 1]})
        self.assertEqual(output, 2)
        self.assertEqual(equation, {"+": [1, 1]})

        output, equation = jsonLogic({"*": [2, 3]})
        self.assertEqual(output, 6)
        self.assertEqual(equation, {"*": [2, 3]})

        output, equation = jsonLogic({"-": [3, 2]})
        self.assertEqual(output, 1)
        self.assertEqual(equation, {"-": [3, 2]})

        output, equation = jsonLogic({"/": [2, 4]})
        self.assertEqual(output, 0.5)
        self.assertEqual(equation, {"/": [2, 4]})

        output, equation = jsonLogic({"+": [1, 1]})
        self.assertEqual(output, 2)
        self.assertEqual(equation, {"+": [1, 1]})

        # Because addition and multiplication are associative,
        # they happily take as many args as you want:
        output, equation = jsonLogic({"+": [1, 1, 1, 1, 1]})
        self.assertEqual(output, 5)
        self.assertEqual(equation, {"+": [1, 1, 1, 1, 1]})

        output, equation = jsonLogic({"*": [2, 2, 2, 2, 2]})
        self.assertEqual(output, 32)
        self.assertEqual(equation, {"*": [2, 2, 2, 2, 2]})

        # Passing just one argument to - returns its arithmetic
        # negative (additive inverse).
        output, equation = jsonLogic({"-": [2]})
        self.assertEqual(output, -2)
        self.assertEqual(equation, {"-": [2]})

        output, equation = jsonLogic({"-": [-2]})
        self.assertEqual(output, 2)
        self.assertEqual(equation, {"-": [-2]})

        # Passing just one argument to + casts it to a number.
        output, equation = jsonLogic({"+": "0"})
        self.assertEqual(output, 0)
        self.assertEqual(equation, {"+": ["0"]})

    def test_modulo(self):
        """
        Modulo. Finds the remainder after the first argument
        is divided by the second argument.
        """
        output, equation = jsonLogic({"%": [101, 2]})
        self.assertEqual(output, 1)
        self.assertEqual(equation, {"%": [101, 2]})

    def test_merge(self):
        """
        Takes one or more arrays, and merges them into one array.
        If arguments aren't arrays, they get cast to arrays.
        """
        output, equation = jsonLogic({"merge": [[1, 2], [3, 4]]})
        self.assertEqual(output, [1, 2, 3, 4])
        self.assertEqual(equation, {"merge": [[1, 2], [3, 4]]})

        output, equation = jsonLogic({"merge": [1, 2, [3, 4]]})
        self.assertEqual(output, [1, 2, 3, 4])
        self.assertEqual(equation, {"merge": [1, 2, [3, 4]]})

        # Merge can be especially useful when defining complex missing rules,
        # like which fields are required in a document. For example, the this
        # vehicle paperwork always requires the car's VIN, but only needs
        # the APR and term if you're financing.
        missing = {
            "missing": {"merge": ["vin", {"if": [{"var": "financing"}, ["apr", "term"], []]}]}
        }
        output, equation = jsonLogic(missing, {"financing": True})
        self.assertEqual(output, ["vin", "apr", "term"])
        self.assertEqual(equation, {"missing": [{"merge": ["vin", ["apr", "term"]]}]})

        output, equation = jsonLogic(missing, {"financing": False})
        self.assertEqual(output, ["vin"])
        self.assertEqual(equation, {"missing": [{"merge": ["vin", []]}]})

    def test_in(self):
        """
        If the second argument is a string, tests that the first argument
        is a substring:
        """
        output, equation = jsonLogic({"in": ["Spring", "Springfield"]})
        self.assertTrue(output)
        self.assertEqual(equation, {"in": ["Spring", "Springfield"]})

    def test_cat(self):
        """
        Concatenate all the supplied arguments. Note that this is not
        a join or implode operation, there is no "glue" string.
        """
        output, equation = jsonLogic({"cat": ["I love", " pie"]})
        self.assertEqual(output, "I love pie")
        self.assertEqual(equation, {"cat": ["I love", " pie"]})

        output, equation = jsonLogic(
            {"cat": ["I love ", {"var": "filling"}, " pie"]}, {"filling": "apple", "temp": 110}
        )
        self.assertEqual(output, "I love apple pie")
        self.assertEqual(
            equation,
            {"cat": ["I love ", {"var": ["filling"]}, " pie"]},
            {"filling": "apple", "temp": 110},
        )

    def test_log(self):
        """
        Logs the first value to console, then passes it through unmodified.
        This can be especially helpful when debugging a large rule.
        """
        output, equation = jsonLogic({"log": "apple"})
        self.assertEqual(output, "apple")
        self.assertEqual(equation, {"log": ["apple"]})


class SharedTests(unittest.TestCase):
    """This runs the tests from http://jsonlogic.com/tests.json."""

    cnt = 0

    @classmethod
    def create_test(cls, logic, data, expected):
        """Adds new test to the class."""

        def test(self):
            """Actual test function."""
            self.assertEqual(jsonLogic(logic, data)[0], expected)

        test.__doc__ = "{},  {}  =>  {}".format(logic, data, expected)
        setattr(cls, "test_{}".format(cls.cnt), test)
        cls.cnt += 1


SHARED_TESTS = json.loads(urlopen("http://jsonlogic.com/tests.json").read().decode("utf-8"))
for item in SHARED_TESTS:
    if isinstance(item, list):
        SharedTests.create_test(*item)
