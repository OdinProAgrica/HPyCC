"""
This module contains old_tests for hpycc.connection.

"""
import os
import subprocess
from tempfile import TemporaryDirectory
import unittest
import re

import pandas as pd
import requests
from requests.exceptions import ConnectionError

import hpycc.connection
from tests.test_helpers import hpcc_functions


# noinspection PyPep8Naming
def setUpModule():
    a = hpcc_functions.start_hpcc_container()
    hpcc_functions.start_hpcc(a)


# noinspection PyPep8Naming
def tearDownModule():
    hpcc_functions.stop_hpcc_container()


class TestConnectionTestConnectionWithNoAuth(unittest.TestCase):
    def test_test_connection_passes_successfully_with_username(self):
        conn = hpycc.connection.Connection(username="testuser")
        result = conn.test_connection()
        self.assertTrue(result)

    def test_test_connection_works_with_numeric_server(self):
        conn = hpycc.connection.Connection(username="test", server="127.0.0.1")
        result = conn.test_connection()
        self.assertTrue(result)

    def test_test_connection_fails_with_incorrect_server(self):
        with self.assertRaises(ConnectionError):
            conn = hpycc.connection.Connection(username="test", server="l")
            conn.test_connection()

    def test_test_connection_fails_with_incorrect_port(self):
        with self.assertRaises(ConnectionError):
            conn = hpycc.connection.Connection(username="test", port=9999)
            conn.test_connection()

    def test_test_connection_passes_with_password(self):
        conn = hpycc.connection.Connection(username="test", password="pw")
        result = conn.test_connection()
        self.assertTrue(result)


class TestConnectionRunECLScriptWithServer(unittest.TestCase):
    def test_run_script_runs_script(self):
        conn = hpycc.Connection("user", test_conn=False)
        good_script = "output(2);"
        with TemporaryDirectory() as d:
            p = os.path.join(d, "test.ecl")
            with open(p, "w+") as file:
                file.write(good_script)
            self.assertTrue(conn.run_ecl_script(p, syntax_check=False,
                                                delete_workunit=False))

    def test_run_script_returns_correct_tuple(self):
        conn = hpycc.Connection("user", test_conn=False)
        good_script = "output(2);"
        expected_out_stdout = "\r\n".join(["Using eclcc path ", "",
                                           "Deploying ECL Archive ", "",
                                           "Deployed",
                                           "   wuid: W20180627-154140",
                                           "   state: compiled", "",
                             "Running deployed workunit W20180627-154140",
            "<Result>", "<Dataset name='Result 1'>",
            " <Row><Result_1>2</Result_1></Row>",
            "</Dataset>", "</Result>\r\n"
                                           ])
        expected_out_stderr = "\r\n".join(["EXEC: Creating PIPE process : ",
                "EXEC: Pipe: Waiting for process to complete 748",
                "EXEC: Pipe: process complete\r\n"
                                           ])
        with TemporaryDirectory() as d:
            p = os.path.join(d, "test.ecl")
            with open(p, "w+") as file:
                file.write(good_script)
            result = conn.run_ecl_script(p, syntax_check=False,
                                         delete_workunit=False)
        self.assertEqual(result.__class__.__name__, "Result")
        stdout_output = re.sub("path (.+?)eclcc", 'path ',
                               result.stdout)
        stdout_output1 = re.sub("Archive (.+?)test.ecl", 'Archive ',
                                stdout_output)
        stdout_output2 = re.sub("W[0-9{8}](\S*)", 'W20180627-154140',
                                stdout_output1)
        self.assertEqual(stdout_output2, expected_out_stdout)
        stderr_output = re.sub(" [0-9][0-9][0-9]", ' 748', result.stderr)
        stderr_output1 = re.sub("process : (.+?)test.ecl\"", 'process : ', stderr_output)
        self.assertEqual(stderr_output1, expected_out_stderr)

    def test_run_script_fails_if_file_not_found(self):
        conn = hpycc.Connection("user", test_conn=False)
        with self.assertRaises(subprocess.SubprocessError):
            conn.run_ecl_script("test.ecl", syntax_check=False, delete_workunit=False)


class TestRunURLRequestWithServer(unittest.TestCase):
    def test_run_url_request_returns_response(self):
        conn = hpycc.Connection("user", test_conn=False)
        result = conn.run_url_request("http://localhost:8010", max_attempts=1,
                                      max_sleep=0)
        self.assertIsInstance(result, requests.Response)


class TestConnectionGetLogicalFileChunkWithServer(unittest.TestCase):
    def test_get_logical_file_chunk_returns_correct_json(self):
        expected_result = [
            {'a': '1', 'b': 'a'},
            {'a': '2', 'b': 'b'},
        ]
        conn = hpycc.Connection("user")
        df = pd.DataFrame({"a": [1, 2, 3], "b": ["a", "b", "c"]})
        with TemporaryDirectory() as d:
            p = os.path.join(d, "data.csv")
            df.to_csv(p, index=False)
            lf_name = "test_get_logical_file_chunk_returns_correct_json"
            hpycc.spray_file(conn, p, lf_name, chunk_size=3, delete_workunit=False)

        result = conn.get_logical_file_chunk(
            "thor::{}".format(lf_name), 0, 2, 3, 2)
        for i in result:
            i.pop("__fileposition__")
        self.assertEqual(expected_result, result)

    def test_get_logical_file_chunk_is_zero_indexed(self):
        expected_result = [
            {'__fileposition__': '0', 'a': '1', 'b': 'a'}
        ]
        conn = hpycc.Connection("user")
        df = pd.DataFrame({"a": [1, 2, 3], "b": ["a", "b", "c"]})
        with TemporaryDirectory() as d:
            p = os.path.join(d, "data.csv")
            df.to_csv(p, index=False)
            hpycc.spray_file(conn, p, "data", chunk_size=3, delete_workunit=False)

        result = conn.get_logical_file_chunk("thor::data", 0, 1, 3, 0)
        self.assertIsInstance(result, list)
        self.assertIsInstance(result[0], dict)
        self.assertEqual(result, expected_result)


class TestConnectionRunECLStringWithServer(unittest.TestCase):
    def test_run_ecl_string_returns_result_of_run_ecl_script(self):
        expected_out_stdout = "\r\n".join(["Using eclcc path ", "",
                                           "Deploying ECL Archive ", "",
                                           "Deployed",
                                           "   wuid: W20180627-154140",
                                           "   state: compiled", "",
                             "Running deployed workunit W20180627-154140",
            "<Result>", "<Dataset name='Result 1'>",
            " <Row><Result_1>2</Result_1></Row>",
            "</Dataset>", "</Result>\r\n"
                                           ])
        expected_out_stderr = "\r\n".join(["EXEC: Creating PIPE process : ",
                "EXEC: Pipe: Waiting for process to complete 748",
                "EXEC: Pipe: process complete\r\n"
                                           ])
        conn = hpycc.Connection("user", test_conn=False)
        result = conn.run_ecl_string("OUTPUT(2);", syntax_check=True,
                                     delete_workunit=False)
        self.assertEqual(result.__class__.__name__, "Result")
        stdout_output = re.sub("path (.+?)eclcc", 'path ',
                               result.stdout)
        stdout_output1 = re.sub("Archive (.+?)_string.ecl", 'Archive ',
                                stdout_output)
        stdout_output2 = re.sub("W[0-9{8}](\S*)", 'W20180627-154140',
                                stdout_output1)
        self.assertEqual(stdout_output2, expected_out_stdout)
        stderr_output = re.sub(" [0-9][0-9][0-9]", ' 748', result.stderr)
        stderr_output1 = re.sub("process : (.+?).ecl\"", 'process : ', stderr_output)
        self.assertEqual(stderr_output1, expected_out_stderr)
