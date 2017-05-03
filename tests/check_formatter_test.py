"""
Health Check Formatter
"""

import unittest
from envmgr_healthchecks.health_checks.check_formatter import CheckFormatter

HTTP_CHECK = {
    'name': 'health_check',
    'http': "https://localhost:${PORT}/something"
}

NON_HTTP_CHECK = {
    'name': 'health_check'
}

INFO = {
    'port': '3333'
}


class TestCheckFormatter(unittest.TestCase):
    """ Check Formatter Tests """

    def setUp(self):
        self.check_formatter = CheckFormatter()

    def test_format_http(self):
        """ When the check has an http value, the port value is replaced """
        self.check_formatter.format(check=HTTP_CHECK, info=INFO)
        self.assertEqual(self.check_formatter.check['http'],
                         formatted_http())

    def test_format_non_http_check(self):
        """ When the check has no http, it is left alone """
        self.check_formatter = CheckFormatter()
        try:
            self.check_formatter.format(check=NON_HTTP_CHECK, info=INFO)
        except Exception:
            self.fail("format() raised Exception unexpectedly!")
        self.assertEqual(self.check_formatter.check, NON_HTTP_CHECK)

    def test_returns_formatted_check(self):
        """ The formatter should return a newly formatted check """
        new_check = self.check_formatter.format(check=HTTP_CHECK, info=INFO)
        expected_check = HTTP_CHECK
        expected_check['http'] = formatted_http()
        self.assertEqual(new_check, expected_check)

def formatted_http():
    """ helper: provide formatted http expectation """
    return 'https://localhost:' + INFO['port'] + '/something'
