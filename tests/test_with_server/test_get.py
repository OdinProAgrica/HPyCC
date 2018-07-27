from concurrent.futures import ThreadPoolExecutor
import os
import subprocess
import unittest
import warnings
from tempfile import TemporaryDirectory
from unittest.mock import patch

import numpy as np
import pandas as pd

import hpycc
from hpycc.get import get_thor_file
from tests.test_helpers import hpcc_functions


# noinspection PyPep8Naming
def setUpModule():
    a = hpcc_functions.start_hpcc_container()
    hpcc_functions.start_hpcc(a)


# noinspection PyPep8Naming
def tearDownModule():
    hpcc_functions.stop_hpcc_container()


def _spray_df(conn, df, name):
    with TemporaryDirectory() as d:
        p = os.path.join(d, "test.csv")
        df.to_csv(p, index=False)
        hpycc.spray_file(conn, p, name)


def _get_output_from_ecl_string(conn, string, syntax=True,
                                delete_workunit=True):
    with TemporaryDirectory() as d:
        p = os.path.join(d, "test.ecl")
        with open(p, "w+") as file:
            file.write(string)
        res = hpycc.get_output(conn, p, syntax, delete_workunit)
        return res


def _get_outputs_from_ecl_string(conn, string, syntax=True,
                                 delete_workunit=True):
    with TemporaryDirectory() as d:
        p = os.path.join(d, "test.ecl")
        with open(p, "w+") as file:
            file.write(string)
        res = hpycc.get_outputs(conn, p, syntax, delete_workunit)
        return res


class TestGetOutputWithServer(unittest.TestCase):
    def setUp(self):
        self.conn = hpycc.Connection("user")

    def test_get_output_returns_single_value_int(self):
        script = "OUTPUT(2);"
        res = _get_output_from_ecl_string(self.conn, script)
        expected = pd.DataFrame({"Result_1": 2}, index=[0])
        pd.testing.assert_frame_equal(expected, res)

    def test_get_output_returns_single_value_str(self):
        script = "OUTPUT('a');"
        res = _get_output_from_ecl_string(self.conn, script)
        expected = pd.DataFrame({"Result_1": 'a'}, index=[0])
        pd.testing.assert_frame_equal(expected, res)

    def test_get_output_returns_dataset(self):
        script = "OUTPUT(DATASET([{1, 'a'}], {INTEGER a; STRING b;}));"
        res = _get_output_from_ecl_string(self.conn, script)
        expected = pd.DataFrame({"a": 1, "b": "a"},
                                index=[0])
        pd.testing.assert_frame_equal(expected, res)

    def test_get_output_only_returns_first_output(self):
        script = "OUTPUT('a'); OUTPUT(1);"
        res = _get_output_from_ecl_string(self.conn, script)
        expected = pd.DataFrame({"Result_1": 'a'}, index=[0])
        pd.testing.assert_frame_equal(expected, res)

    def test_get_output_parses_bools_all_true(self):
        script = "OUTPUT(DATASET([{true}, {true}], {BOOLEAN a;}));"
        res = _get_output_from_ecl_string(self.conn, script)
        expected = pd.DataFrame({"a": [True, True]})
        pd.testing.assert_frame_equal(expected, res)

    def test_get_output_parses_bools_all_false(self):
        script = "OUTPUT(DATASET([{false}, {false}], {BOOLEAN a;}));"
        res = _get_output_from_ecl_string(self.conn, script)
        expected = pd.DataFrame({"a": [False, False]})
        pd.testing.assert_frame_equal(expected, res)

    def test_get_output_parses_bools_true_and_false(self):
        script = "OUTPUT(DATASET([{true}, {false}], {BOOLEAN a;}));"
        res = _get_output_from_ecl_string(self.conn, script)
        expected = pd.DataFrame({"a": [True, False]})
        pd.testing.assert_frame_equal(expected, res)

    def test_get_output_parses_bools_true_and_false_strings(self):
        script = "OUTPUT(DATASET([{'true'}, {'false'}], {STRING a;}));"
        res = _get_output_from_ecl_string(self.conn, script)
        expected = pd.DataFrame({"a": [True, False]})
        pd.testing.assert_frame_equal(expected, res)

    def test_get_output_parses_bools_true_and_false_strings_with_blank(self):
        script = "OUTPUT(DATASET([{'true'}, {'false'}, {''}], {STRING a;}));"
        res = _get_output_from_ecl_string(self.conn, script)
        expected = pd.DataFrame({"a": [True, False, np.nan]})
        pd.testing.assert_frame_equal(expected, res)

    def test_get_output_parses_blank_string_as_nan(self):
        script = "OUTPUT(DATASET([{''}], {STRING a;}));"
        res = _get_output_from_ecl_string(self.conn, script)
        expected = pd.DataFrame({"a": [np.nan]}, index=[0])
        pd.testing.assert_frame_equal(expected, res)

    def test_get_output_parses_ints(self):
        script = "OUTPUT(DATASET([{1}, {2}], {INTEGER a;}));"
        res = _get_output_from_ecl_string(self.conn, script)
        expected = pd.DataFrame({"a": [1, 2]})
        pd.testing.assert_frame_equal(expected, res)

    def test_get_output_parses_floats(self):
        script = "OUTPUT(DATASET([{1.0}, {2.1}], {REAL a;}));"
        res = _get_output_from_ecl_string(self.conn, script)
        expected = pd.DataFrame({"a": [1.0, 2.1]})
        pd.testing.assert_frame_equal(expected, res)

    def test_get_output_parses_mixed_floats_and_ints(self):
        script = "OUTPUT(DATASET([{1}, {2.1}], {REAL a;}));"
        res = _get_output_from_ecl_string(self.conn, script)
        expected = pd.DataFrame({"a": [1, 2.1]})
        pd.testing.assert_frame_equal(expected, res)

    def test_get_output_parses_numbers_as_strings(self):
        script = "OUTPUT(DATASET([{'1'}, {'2.1'}], {STRING a;}));"
        res = _get_output_from_ecl_string(self.conn, script)
        expected = pd.DataFrame({"a": [1, 2.1]})
        pd.testing.assert_frame_equal(expected, res)

    def test_get_output_parses_empty_dataset(self):
        script = "a := DATASET([{'a'}, {'a'}], {STRING a;});a(a != 'a');"
        with warnings.catch_warnings(record=True) as w:
            res = _get_output_from_ecl_string(self.conn, script)
            self.assertEqual(len(w), 1)
            expected_warn = ("The output does not appear to contain a "
                             "dataset. Returning an empty DataFrame.")
            self.assertEqual(str(w[-1].message), expected_warn)
        expected = pd.DataFrame()
        pd.testing.assert_frame_equal(expected, res)

    def test_get_output_parses_mixed_columns_as_strings(self):
        script = "OUTPUT(DATASET([{'1'}, {'a'}], {STRING a;}));"
        res = _get_output_from_ecl_string(self.conn, script)
        expected = pd.DataFrame({"a": ['1', 'a']})
        pd.testing.assert_frame_equal(expected, res)

    def test_get_output_raises_with_bad_script(self):
        script = "asa"
        with self.assertRaises(subprocess.SubprocessError):
            _get_output_from_ecl_string(self.conn, script)

    @patch.object(hpycc.Connection, "check_syntax")
    def test_get_output_runs_syntax_check_if_true(self, mock):
        script = "OUTPUT(2);"
        _get_output_from_ecl_string(self.conn, script)
        mock.assert_called()

    @patch.object(hpycc.Connection, "check_syntax")
    def test_get_output_doesnt_run_syntax_check_if_false(self, mock):
        script = "OUTPUT(2);"
        _get_output_from_ecl_string(self.conn, script, syntax=False)
        self.assertFalse(mock.called)

    @patch.object(hpycc.connection.delete, "delete_workunit")
    def test_get_output_runs_delete_workunit_if_true(self, mock):
        script = "OUTPUT(2);"
        _get_output_from_ecl_string(self.conn, script, delete_workunit=True)
        mock.assert_called()

    @patch.object(hpycc.connection.delete, "delete_workunit")
    def test_get_output_doesnt_run_delete_workunit_if_false(self, mock):
        script = "OUTPUT(2);"
        _get_output_from_ecl_string(self.conn, script, delete_workunit=False)
        self.assertFalse(mock.called)


class TestGetOutputsWithServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.conn = hpycc.Connection("user")
        script = ("OUTPUT(2);OUTPUT('a');OUTPUT(DATASET([{1, 'a'}], "
                  "{INTEGER a; STRING b;}), NAMED('ds'));")
        cls.res = _get_outputs_from_ecl_string(cls.conn, script)
        a = [
            {"col": "alltrue", "content": "[{true}, {true}, {true}]",
             "coltype": "BOOLEAN"},
            {"col": "allfalse", "content": "[{false}, {false}, {false}]",
             "coltype": "BOOLEAN"},
            {"col": "trueandfalse", "content": "[{true}, {false}, {true}]",
             "coltype": "BOOLEAN"},
            {"col": "truefalsestrings",
             "content": "[{'true'}, {'false'}, {'false'}]",
             "coltype": "STRING"},
            {"col": "truefalseblank", "content": "[{'true'}, {'false'}, {''}]",
             "coltype": "STRING"}
        ]
        f = [("OUTPUT(DATASET({0[content]}, {{{0[coltype]} {0[col]};}}), "
             "NAMED('{0[col]}'));").format(i) for i in a]
        cls.t_f_res = _get_outputs_from_ecl_string(cls.conn, "\n".join(f))

    def test_get_outputs_returns_single_value_int(self):
        expected = pd.DataFrame({"Result_1": 2}, index=[0])
        pd.testing.assert_frame_equal(expected, self.res["Result_1"])

    def test_get_outputs_returns_single_value_str(self):
        expected = pd.DataFrame({"Result_2": 'a'}, index=[0])
        pd.testing.assert_frame_equal(expected, self.res["Result_2"])

    def test_get_outputs_returns_dataset(self):
        expected = pd.DataFrame({"a": 1, "b": "a"},
                                index=[0])
        pd.testing.assert_frame_equal(expected, self.res["ds"])

    def test_get_outputs_returns_all_outputs(self):
        self.assertEqual(list(self.res.keys()), ["Result_1", "Result_2", "ds"])

    def test_get_outputs_parses_bools_all_true(self):
        expected = pd.DataFrame({"alltrue": [True, True, True]})
        pd.testing.assert_frame_equal(expected, self.t_f_res["alltrue"])

    def test_get_outputs_parses_bools_all_false(self):
        expected = pd.DataFrame({"allfalse": [False, False, False]})
        pd.testing.assert_frame_equal(expected, self.t_f_res["allfalse"])

    def test_get_outputs_parses_bools_true_and_false(self):
        expected = pd.DataFrame({"trueandfalse": [True, False, True]})
        pd.testing.assert_frame_equal(expected, self.t_f_res["trueandfalse"])

    def test_get_outputs_parses_bools_true_and_false_strings(self):
        expected = pd.DataFrame({"truefalsestrings": [True, False, False]})
        pd.testing.assert_frame_equal(
            expected, self.t_f_res["truefalsestrings"])

    def test_get_outputs_parses_bools_true_and_false_strings_with_blank(self):
        expected = pd.DataFrame({"truefalseblank": [True, False, np.nan]})
        pd.testing.assert_frame_equal(expected, self.t_f_res["truefalseblank"])

    def test_get_outputs_parses_blank_string_as_nan(self):
        script = "OUTPUT(DATASET([{''}], {STRING a;}));"
        res = _get_outputs_from_ecl_string(self.conn, script)
        expected = pd.DataFrame({"a": [np.nan]}, index=[0])
        pd.testing.assert_frame_equal(expected, res["Result_1"])

    def test_get_outputs_parses_ints(self):
        script = "OUTPUT(DATASET([{1}, {2}], {INTEGER a;}));"
        res = _get_outputs_from_ecl_string(self.conn, script)
        expected = pd.DataFrame({"a": [1, 2]})
        pd.testing.assert_frame_equal(expected, res["Result_1"])

    def test_get_outputs_parses_floats(self):
        script = "OUTPUT(DATASET([{1.0}, {2.1}], {REAL a;}));"
        res = _get_outputs_from_ecl_string(self.conn, script)
        expected = pd.DataFrame({"a": [1.0, 2.1]})
        pd.testing.assert_frame_equal(expected, res["Result_1"])

    def test_get_outputs_parses_mixed_floats_and_ints(self):
        script = "OUTPUT(DATASET([{1}, {2.1}], {REAL a;}));"
        res = _get_outputs_from_ecl_string(self.conn, script)
        expected = pd.DataFrame({"a": [1, 2.1]})
        pd.testing.assert_frame_equal(expected, res["Result_1"])

    def test_get_outputs_parses_numbers_as_strings(self):
        script = "OUTPUT(DATASET([{'1'}, {'2.1'}], {STRING a;}));"
        res = _get_outputs_from_ecl_string(self.conn, script)
        expected = pd.DataFrame({"a": [1, 2.1]})
        pd.testing.assert_frame_equal(expected, res["Result_1"])

    def test_get_outputs_parses_empty_dataset(self):
        script = ("a := DATASET([{'a'}, {'a'}], {STRING a;});a(a != 'a');"
                  "OUTPUT(2);")

        with warnings.catch_warnings(record=True) as w:
            res = _get_outputs_from_ecl_string(self.conn, script)
            self.assertEqual(len(w), 1)
            expected_warn = (
                "One or more of the outputs do not appear to contain a "
                "dataset. They have been replaced with an empty DataFrame")
            self.assertEqual(str(w[-1].message), expected_warn)
        self.assertEqual(list(res.keys()), ["Result_1", "Result_2"])
        pd.testing.assert_frame_equal(res["Result_1"], pd.DataFrame())

    def test_get_outputs_parses_mixed_columns_as_strings(self):
        script = "OUTPUT(DATASET([{'1'}, {'a'}], {STRING a;}));"
        res = _get_outputs_from_ecl_string(self.conn, script)
        expected = pd.DataFrame({"a": ['1', 'a']})
        pd.testing.assert_frame_equal(expected, res["Result_1"])

    def test_get_outputs_raises_with_bad_script(self):
        script = "asa"
        with self.assertRaises(subprocess.SubprocessError):
            _get_outputs_from_ecl_string(self.conn, script)

    @patch.object(hpycc.Connection, "check_syntax")
    def test_get_outputs_runs_syntax_check_if_true(self, mock):
        script = "OUTPUT(2);"
        _get_outputs_from_ecl_string(self.conn, script)
        mock.assert_called()

    @patch.object(hpycc.Connection, "check_syntax")
    def test_get_outputs_doesnt_run_syntax_check_if_false(self, mock):
        script = "OUTPUT(2);"
        _get_outputs_from_ecl_string(self.conn, script, False)
        self.assertFalse(mock.called)

    @patch.object(hpycc.connection.delete, "delete_workunit")
    def test_get_outputs_runs_delete_workunit_if_true(self, mock):
        script = "OUTPUT(2);"
        _get_outputs_from_ecl_string(self.conn, script)
        mock.assert_called()

    @patch.object(hpycc.connection.delete, "delete_workunit")
    def test_get_outputs_doesnt_run_delete_workunit_if_false(self, mock):
        script = "OUTPUT(2);"
        _get_outputs_from_ecl_string(self.conn, script, delete_workunit=False)
        self.assertFalse(mock.called)


class TestGetThorFile(unittest.TestCase):
    def setUp(self):
        self.conn = hpycc.Connection("user", test_conn=False)

    def test_get_thor_file_returns_empty_dataset(self):
        self.conn.run_ecl_string(
            "a := DATASET([], {INTEGER int;}); "
            "OUTPUT(a,,'~test_get_thor_file_returns_empty_dataset');",
            True,
            True
        )
        res = get_thor_file(
            connection=self.conn,
            thor_file="test_get_thor_file_returns_empty_dataset")
        expected = pd.DataFrame(columns=["int", "__fileposition__"])
        pd.testing.assert_frame_equal(expected, res)

    def test_get_thor_file_returns_single_row_dataset(self):
        self.conn.run_ecl_string(
            "a := DATASET([{1}], {INTEGER int;}); "
            "OUTPUT(a,,'~test_get_thor_file_returns_single_row_dataset');",
            True,
            True
        )
        res = get_thor_file(
            connection=self.conn,
            thor_file="test_get_thor_file_returns_single_row_dataset")
        expected = pd.DataFrame({"int": [1], "__fileposition__": 0})
        pd.testing.assert_frame_equal(expected, res, check_column_type=False,
                                      check_dtype=False)

    def test_get_thor_file_returns_100_row_dataset(self):
        lots_of_1s = "[" + ",".join(["{1}"]*100) + "]"
        self.conn.run_ecl_string(
            "a := DATASET({}, {{INTEGER int;}}); "
            "OUTPUT(a,,'~test_get_thor_file_returns_100_row_dataset');".format(
                lots_of_1s),
            True,
            True
        )
        res = get_thor_file(
            connection=self.conn,
            thor_file="test_get_thor_file_returns_100_row_dataset")
        expected = pd.DataFrame({
            "int": [1]*100,
            "__fileposition__": [i*8 for i in range(100)]
        })
        pd.testing.assert_frame_equal(expected, res, check_column_type=False,
                                      check_dtype=False)

    def test_get_thor_file_works_when_num_rows_less_than_chunksize(self):
        file_name = ("test_get_thor_file_works_when_num_rows_less_than_"
                     "chunksize")
        self.conn.run_ecl_string(
            "a := DATASET([{{1}}], {{INTEGER int;}}); "
            "OUTPUT(a,,'~{}');".format(file_name),
            True,
            True
        )
        res = get_thor_file(
            connection=self.conn, thor_file=file_name, chunk_size=2)
        expected = pd.DataFrame({"int": [1], "__fileposition__": 0})
        pd.testing.assert_frame_equal(expected, res, check_dtype=False)

    def test_get_thor_file_works_when_num_rows_equal_to_chunksize(self):
        file_name = "test_get_thor_file_works_when_num_rows_equal_to_chunksize"
        self.conn.run_ecl_string(
            "a := DATASET([{{1}}, {{2}}], {{INTEGER int;}}); "
            "OUTPUT(a,,'~{}');".format(file_name),
            True,
            True
        )
        res = get_thor_file(
            connection=self.conn, thor_file=file_name, chunk_size=2)
        expected = pd.DataFrame({"int": [1, 2], "__fileposition__": [0, 8]})
        pd.testing.assert_frame_equal(expected, res, check_dtype=False)

    def test_get_thor_file_works_when_num_rows_greater_than_chunksize(self):
        file_name = ("test_get_thor_file_works_when_num_rows_greater_than_"
                     "chunksize")
        self.conn.run_ecl_string(
            "a := DATASET([{{1}}, {{2}}], {{INTEGER int;}}); "
            "OUTPUT(a,,'~{}');".format(file_name),
            True,
            True
        )
        res = get_thor_file(
            connection=self.conn,
            thor_file=file_name, chunk_size=1)
        expected = pd.DataFrame({"int": [1, 2], "__fileposition__": [0, 8]})
        res = res.sort_values("__fileposition__")
        pd.testing.assert_frame_equal(
            expected, res, check_index_type=False, check_column_type=False,
            check_dtype=False, check_like=False)

    @patch.object(hpycc.connection.Connection, "get_logical_file_chunk")
    def test_get_thor_file_chunks_when_num_rows_less_than_chunksize(
            self, mock):
        file_name = ("test_get_thor_file_chunks_when_num_rows_less_than"
                     "_chunksize")
        mock.return_value = [{'int': '1', '__fileposition__': '0'}]
        self.conn.run_ecl_string(
            "a := DATASET([{{1}}], {{INTEGER int;}}); "
            "OUTPUT(a,,'~{}');".format(file_name),
            True,
            True
        )
        get_thor_file(
            connection=self.conn, thor_file=file_name, chunk_size=3)
        mock.assert_called_with(file_name, 0, 1, 3, 10)

    @patch.object(hpycc.connection.Connection, "get_logical_file_chunk")
    def test_get_thor_file_chunks_when_num_rows_equal_to_chunksize(self, mock):
        file_name = ("test_get_thor_file_chunks_when_num_rows_equal_to_"
                     "chunksize")
        mock.return_value = [{'int': '1', '__fileposition__': '0'}]
        self.conn.run_ecl_string(
            "a := DATASET([{{1}}, {{2}}], {{INTEGER int;}}); "
            "OUTPUT(a,,'~{}');".format(file_name),
            True,
            True
        )
        get_thor_file(
            connection=self.conn, thor_file=file_name, chunk_size=2)
        mock.assert_called_with(file_name, 0, 2, 3, 10)

    @patch.object(hpycc.connection.Connection, "get_logical_file_chunk")
    def test_get_thor_file_chunks_when_num_rows_greater_than_chunksize(
            self, mock):
        file_name = ("test_get_thor_file_chunks_when_num_rows_greater_than_"
                     "chunksize")
        mock.return_value = [{'int': '1', '__fileposition__': '0'}]
        self.conn.run_ecl_string(
           "a := DATASET([{{1}}, {{2}}], {{INTEGER int;}}); "
           "OUTPUT(a,,'~{}');".format(file_name),
           True,
           True
        )
        get_thor_file(
            connection=self.conn, thor_file=file_name, chunk_size=1)
        expected = [
            unittest.mock.call(file_name, 0, 1, 3, 10),
            unittest.mock.call(file_name, 1, 1, 3, 10)
        ]
        self.assertEqual(expected, mock.call_args_list)

    @patch.object(hpycc.connection.Connection, "get_logical_file_chunk")
    def test_get_thor_file_uses_default_chunk_size(self, mock):
        file_name = "test_get_thor_file_uses_default_chunk_size"
        mock.return_value = [{'int': '1', '__fileposition__': '0'}]
        self.conn.run_ecl_string(
           "a := DATASET([{}], {{INTEGER int;}}); "
           "OUTPUT(a,,'~{}');".format(",".join(["{1}"]*10001), file_name),
           True,
           True
        )
        get_thor_file(
            connection=self.conn, thor_file=file_name)
        expected = [
            unittest.mock.call(file_name, 0, 10000, 3, 10),
            unittest.mock.call(file_name, 10000, 1, 3, 10)
        ]
        self.assertEqual(expected, mock.call_args_list)

    def test_get_thor_file_works_when_chunksize_is_zero(self):
        file_name = "test_get_thor_file_works_when_chunksize_is_zero"
        self.conn.run_ecl_string(
            "a := DATASET([{{1}}, {{2}}], {{INTEGER int;}}); "
            "OUTPUT(a,,'~{}');".format(file_name),
            True,
            True
        )
        with self.assertRaises(ZeroDivisionError):
            get_thor_file(connection=self.conn, thor_file=file_name,
                          chunk_size=0)

    def test_get_thor_file_parses_column_types_correctly(self):
        i = 1
        d = 1.5
        u = "U'ABC'"
        s = "'ABC'"
        b = "TRUE"
        x = "x'ABC'"
        es = "ABC"
        types = [("INTEGER", "int", i),
                 ("INTEGER1", "int1", i),
                 ("UNSIGNED INTEGER", "unsigned_int", i),
                 ("UNSIGNED INTEGER1", "unsigned_int_1", i),
                 ("UNSIGNED8", "is_unsigned_8", i),
                 ("UNSIGNED", "usigned", i),
                 ("DECIMAL10", "dec10", d, round(d)),
                 ("DECIMAL5_3", "dec5_3", d),
                 ("UNSIGNED DECIMAL10", "unsigned_dec10", d, round(d)),
                 ("UNSIGNED DECIMAL5_3", "unsigned_decl5_3", d),
                 ("UDECIMAL10", "udec10", d, round(d)),
                 ("UDECIMAL5_3", "udec5_3", d),
                 ("REAL", "is_real", d),
                 ("REAL4", "is_real4", d),
                 ("UNICODE", "ucode", u, es),
                 ("UNICODE_de", "ucode_de", u, es),
                 ("UNICODE3", "ucode4", u, es),
                 ("UNICODE_de3", "ucode_de4", u, es),
                 ("UTF8", "is_utf8", u, es),
                 ("UTF8_de", "is_utf8_de", u, es),
                 ("STRING", "str", s, es),
                 ("STRING3", "str1", s, es),
                 ("ASCII STRING", "ascii_str", s, es),
                 ("ASCII STRING3", "ascii_str1", s, es),
                 ("EBCDIC STRING", "ebcdic_str", s, es),
                 ("EBCDIC STRING3", "ebcdic_str1", s, es),
                 ("BOOLEAN", "bool", b, True),
                 ("DATA", "is_data", x, "0ABC"),
                 ("DATA3", "is_data_16", x, "0ABC00"),
                 ("VARUNICODE", "varucode", u, es),
                 ("VARUNICODE_de", "varucode_de", u, es),
                 ("VARUNICODE3", "varucode4", u, es),
                 ("VARUNICODE_de3", "varucode_de4", u, es),
                 ("VARSTRING", "varstr", u, es),
                 ("VARSTRING3", "varstr3", u, es),
                 ("QSTRING", "qstr", s, es),
                 ("QSTRING3", "qstr8", s, es)]
        for t in types:
            file_name = ("test_get_thor_file_parses_column_types"
                         "_correctly_{}").format(t[1])
            self.conn.run_ecl_string(
                "a := DATASET([{{{}}}], {{{} {};}}); "
                "OUTPUT(a,,'~{}');".format(t[2], t[0], t[1], file_name),
                True,
                True
            )
            try:
                expected_val = t[3]
            except IndexError:
                expected_val = t[2]
            a = get_thor_file(
                connection=self.conn, thor_file=file_name, dtype=None)
            expected = pd.DataFrame(
                {"__fileposition__": [0], t[1]: [expected_val]})
            pd.testing.assert_frame_equal(expected, a, check_dtype=False)

    def test_get_thor_file_parses_set_types_correctly(self):
        i = 1
        d = 1.5
        u = "U'ABC'"
        s = "'ABC'"
        b = "TRUE"
        x = "x'ABC'"
        es = "ABC"
        types = [("INTEGER", "int", i),
                 ("INTEGER1", "int1", i),
                 ("UNSIGNED INTEGER", "unsigned_int", i),
                 ("UNSIGNED INTEGER1", "unsigned_int_1", i),
                 ("UNSIGNED8", "is_unsigned_8", i),
                 ("UNSIGNED", "usigned", i),
                 ("DECIMAL10", "dec10", d, round(d)),
                 ("DECIMAL5_3", "dec5_3", d),
                 ("UNSIGNED DECIMAL10", "unsigned_dec10", d, round(d)),
                 ("UNSIGNED DECIMAL5_3", "unsigned_decl5_3", d),
                 ("UDECIMAL10", "udec10", d, round(d)),
                 ("UDECIMAL5_3", "udec5_3", d),
                 ("REAL", "is_real", d),
                 ("REAL4", "is_real4", d),
                 ("UNICODE", "ucode", u, es),
                 ("UNICODE_de", "ucode_de", u, es),
                 ("UNICODE3", "ucode4", u, es),
                 ("UNICODE_de3", "ucode_de4", u, es),
                 ("UTF8", "is_utf8", u, es),
                 ("UTF8_de", "is_utf8_de", u, es),
                 ("STRING", "str", s, es),
                 ("STRING3", "str1", s, es),
                 ("ASCII STRING", "ascii_str", s, es),
                 ("ASCII STRING3", "ascii_str1", s, es),
                 ("EBCDIC STRING", "ebcdic_str", s, es),
                 ("EBCDIC STRING3", "ebcdic_str1", s, es),
                 ("BOOLEAN", "bool", b, True),
                 ("DATA", "is_data", x, "0ABC"),
                 ("DATA3", "is_data_16", x, "0ABC00"),
                 ("VARUNICODE", "varucode", u, es),
                 ("VARUNICODE_de", "varucode_de", u, es),
                 ("VARUNICODE3", "varucode4", u, es),
                 ("VARUNICODE_de3", "varucode_de4", u, es),
                 ("VARSTRING", "varstr", u, es),
                 ("VARSTRING3", "varstr3", u, es),
                 ("QSTRING", "qstr", s, es),
                 ("QSTRING3", "qstr8", s, es)]
        for t in types:
            file_name = ("test_get_thor_file_parses_set_types_"
                         "correctly_{}").format(t[1])
            s = ("a := DATASET([{{[{}]}}], {{SET OF {} {};}}); "
                 "OUTPUT(a,,'~{}');").format(t[2], t[0], t[1], file_name)
            self.conn.run_ecl_string(s, True, False)
            try:
                expected_val = t[3]
            except IndexError:
                expected_val = t[2]
            a = get_thor_file(connection=self.conn, thor_file=file_name,
                              dtype=None)
            expected = pd.DataFrame(
                {"__fileposition__": [0], t[1]: [[expected_val]]})
            pd.testing.assert_frame_equal(expected, a, check_dtype=False)

    @patch.object(hpycc.get, "ThreadPoolExecutor")
    def test_get_thor_file_uses_default_max_workers(self, mock):
        mock.return_value = ThreadPoolExecutor(max_workers=15)
        file_name = "test_get_thor_file_uses_default_max_workers"
        self.conn.run_ecl_string(
            "a := DATASET([{{1}}, {{2}}], {{INTEGER int;}}); "
            "OUTPUT(a,,'~{}');".format(file_name),
            True,
            True
        )
        get_thor_file(self.conn, file_name)
        mock.assert_called_with(max_workers=15)

    @patch.object(hpycc.get, "ThreadPoolExecutor")
    def test_get_thor_file_uses_custom_max_workers(self, mock):
        mock.return_value = ThreadPoolExecutor(max_workers=15)
        file_name = "test_get_thor_file_uses_custom_max_workers"
        self.conn.run_ecl_string(
            "a := DATASET([{{1}}, {{2}}], {{INTEGER int;}}); "
            "OUTPUT(a,,'~{}');".format(file_name),
            True,
            True
        )
        get_thor_file(self.conn, file_name, max_workers=2)
        mock.assert_called_with(max_workers=2)

    @patch.object(hpycc.connection.Connection, "get_logical_file_chunk")
    def test_get_thor_file_uses_defaults(self, mock):
        mock.return_value = [{"int": 1, "__fileposition__": 0}]
        file_name = "test_get_thor_file_uses_defaults"
        self.conn.run_ecl_string(
            "a := DATASET([{{1}}, {{2}}], {{INTEGER int;}}); "
            "OUTPUT(a,,'~{}');".format(file_name),
            True,
            False
        )
        get_thor_file(self.conn, file_name)
        mock.assert_called_with(file_name, 0, 2, 3, 10)

    @patch.object(hpycc.connection.Connection, "get_logical_file_chunk")
    def test_get_thor_file_uses_max_sleep(self, mock):
        mock.return_value = [{"int": 1, "__fileposition__": 0}]
        file_name = "test_get_thor_file_uses_max_sleep"
        self.conn.run_ecl_string(
            "a := DATASET([{{1}}, {{2}}], {{INTEGER int;}}); "
            "OUTPUT(a,,'~{}');".format(file_name),
            True,
            False
        )
        get_thor_file(self.conn, file_name, max_sleep=20)
        mock.assert_called_with(file_name, 0, 2, 3, 20)

    # test the dtype
    def test_get_thor_file_uses_single_dtype(self):
        file_name = "test_get_thor_file_uses_single_dtype"
        self.conn.run_ecl_string(
            "a := DATASET([{{'1'}}, {{'2'}}], {{STRING int;}}); "
            "OUTPUT(a,,'~{}');".format(file_name),
            True,
            True
        )
        res = get_thor_file(self.conn, file_name, dtype=int)
        expected = pd.DataFrame({"int": [1, 2], "__fileposition__": [0, 5]})
        pd.testing.assert_frame_equal(expected, res, check_dtype=False)

    def test_get_thor_file_uses_dict_of_dtypes(self):
        file_name = "test_get_thor_file_uses_dict_of_dtypes"
        self.conn.run_ecl_string(
            "a := DATASET([{{'1', TRUE, 1}}, {{'2', FALSE, 2}}], "
            "{{STRING str; BOOLEAN bool; INTEGER int;}}); "
            "OUTPUT(a,,'~{}');".format(file_name),
            True,
            True
        )
        res = get_thor_file(
            self.conn, file_name, dtype={"str": int, "bool": bool, "int": str,
                                         "__fileposition__": str})
        expected = pd.DataFrame({
            "int": ["1", "2"],
            "str": [1, 2],
            "bool": [True, False],
            "__fileposition__": ["0", "14"]})
        pd.testing.assert_frame_equal(expected, res, check_dtype=False)

    def test_get_thor_file_uses_dict_of_dtypes_with_missing_cols(self):
        file_name = "test_get_thor_file_uses_dict_of_dtypes_with_missing__cols"
        self.conn.run_ecl_string(
            "a := DATASET([{{'1', TRUE, 1}}, {{'2', FALSE, 2}}], "
            "{{STRING str; BOOLEAN bool; INTEGER int;}}); "
            "OUTPUT(a,,'~{}');".format(file_name),
            True,
            True
        )
        res = get_thor_file(self.conn, file_name,
                            dtype={"bool": bool, "int": str})
        expected = pd.DataFrame({
            "int": ["1", "2"],
            "str": ["1", "2"],
            "bool": [True, False],
            "__fileposition__": ["0", "14"]})
        pd.testing.assert_frame_equal(expected, res, check_dtype=False)

    def test_get_thor_file_uses_dict_of_dtypes_with_extra_cols(self):
        file_name = "test_get_thor_file_uses_dict_of_dtypes_with_extra_cols"
        self.conn.run_ecl_string(
            "a := DATASET([{{'1', TRUE, 1}}, {{'2', FALSE, 2}}], "
            "{{STRING str; BOOLEAN bool; INTEGER int;}}); "
            "OUTPUT(a,,'~{}');".format(file_name),
            True,
            True
        )
        with self.assertRaises(KeyError):
            get_thor_file(self.conn, file_name,
                          dtype={"bool": bool, "int": str, "made_up": str})
