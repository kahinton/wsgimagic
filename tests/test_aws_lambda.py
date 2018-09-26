import unittest
from unittest.mock import MagicMock
import os
import sys


lib_dir = os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')), 'wsgimagic')
if lib_dir not in sys.path:
    sys.path.insert(1, lib_dir)

from aws_lambda import _map_api_gateway_to_request, _basic_error_handler, _build_proxy_response, \
    TranslatedRequest, RawResponse


fake_event = {
    "resource": None,
    "path": '/test',
    "httpMethod": 'GET',
    "headers": {"test": "test"},
    "multiValueHeaders": {"test1": ['1,2,3']},
    "queryStringParameters": {'t': 'test', 't2': 'test2'},
    "multiValueQueryStringParameters": {"mquerytest1": ['1,2,3']},
    "pathParameters":  {},
    "stageVariables": {},
    "requestContext": {},
    "body": "test",
    "isBase64Encoded": False
}


class TestWsgiMagic(unittest.TestCase):
    def test__map_api_gateway_to_request(self):
        # SETUP
        translated = _map_api_gateway_to_request(**fake_event)

        # ASSERT
        needed_result = TranslatedRequest('/test', 'GET', {'HTTP_TEST': 'test',
                                                           'HTTP_TEST1': '1,2,3'},
                                          't=test&t2=test2&mquerytest1=1,2,3', 'test')

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
        fake_response = RawResponse()
        fake_response.result = ['Hello', 'World']
        fake_response.caught_exception: Exception = None
        fake_response.response_status = '200 OK'
        fake_response.outbound_headers = {'Header1': 'H1', 'Header2': 'H2'}

        # ASSERT
        self.assertEqual(_build_proxy_response(fake_response, MagicMock),
                         {'statusCode': '200',
                          'headers': {'Header1': 'H1', 'Header2': 'H2'},
                          'body': 'HelloWorld'})

    def test__build_proxy_response_when_an_error_occurred(self):
        # SETUP
        fake_response = RawResponse()
        fake_response.result = None
        fake_response.caught_exception: Exception = ValueError('Something Broke!!')
        fake_response.response_status = None
        fake_response.outbound_headers = None

        # ASSERT
        error_response = _build_proxy_response(fake_response, _basic_error_handler)
        self.assertEqual(error_response['statusCode'], '500')
        self.assertEqual(error_response['headers']['Server'], 'WSGIMagic')
        self.assertEqual(error_response['body'], 'Server Error')


if __name__ == '__main__':
    unittest.main()
