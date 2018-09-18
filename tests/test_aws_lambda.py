import unittest
from unittest.mock import MagicMock
import os
import sys


lib_dir = os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')), 'wsgimagic')
if lib_dir not in sys.path:
    sys.path.insert(1, lib_dir)

from aws_lambda import _map_api_gateway_to_request, _basic_error_handler, _build_proxy_response, \
    TranslatedRequest


fake_event = {
    "resource": None,
    "path": '/test',
    "httpMethod": 'GET',
    "headers": {"test": "test"},
    "queryStringParameters": {'t': 'test', 't2': 'test2'},
    "pathParameters":  {},
    "stageVariables": {},
    "requestContext": {},
    "body": "test",
    "isBase64Encoded": False
}


class FakeWSGIHandler:
    caught_exception = None
    response_status = '200 Ok'
    outbound_headers = {'Header1': 'H1',
                        'Header2': 'H2'}

    def error_handler(self, e):
        return "Something Bad Happened"


class TestWsgiMagic(unittest.TestCase):
    def test__map_api_gateway_to_request(self):
        # SETUP
        translated = _map_api_gateway_to_request(**fake_event)

        # ASSERT
        needed_result = TranslatedRequest('/test', 'GET', {'HTTP_TEST': 'test'},
                                          't=test&t2=test2', 'test')

        self.assertEqual(translated.__dict__, needed_result.__dict__)

    def test__basic_error_handler(self):
        # SETUP
        bad_result = _basic_error_handler(ValueError('An Error Occurred'))
        del(bad_result['headers']['Date'])

        # ASSERT
        self.assertEqual(bad_result, {'statusCode': '500',
                                      'headers': {'Server': 'WSGIMagic'},
                                      'body': 'Server Error'})

    def test__build_proxy_response_when_all_goes_well(self):
        # SETUP
        test_handler = FakeWSGIHandler()

        # ASSERT
        self.assertEqual(_build_proxy_response(test_handler, ['Hello', 'World']),
                         {'statusCode': '200',
                          'headers': {'Header1': 'H1', 'Header2': 'H2'},
                          'body': 'HelloWorld'})

    def test__build_proxy_response_when_an_error_occurred(self):
        # SETUP
        test_handler = FakeWSGIHandler()
        test_handler.caught_exception = ValueError('Something Broke!')

        # ASSERT
        self.assertEqual(_build_proxy_response(test_handler, ['Hello', 'World']),
                         "Something Bad Happened")


if __name__ == '__main__':
    unittest.main()
