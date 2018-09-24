import unittest
from unittest.mock import MagicMock
import os
import sys


lib_dir = os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')), 'wsgimagic')
if lib_dir not in sys.path:
    sys.path.insert(1, lib_dir)

from magic_core import WSGIHandler, TranslatedRequest


fake_API_event = TranslatedRequest('/test', 'GET', {'HTTP_TEST': 'test'}, 't=test&t2=test2',
                                   'hello')


class FakeWSGIApp:
    pass


def fake_build_response(self, result: 'iterable') -> dict:
    """Once the application completes the request, maps the results into the format required by
    AWS.
    """
    if self.caught_exception is not None:
        return self.error_handler(self.caught_exception)
    return {'status': self.response_status.split(' ')[0],
            'headers': self.outbound_headers,
            'body': ''.join([str(message) for message in result])}


def fake_error_handler(exception: Exception):
    return 'You broke it!'


class TestWsgiMagic(unittest.TestCase):
    def test_get_environment_dictionary(self):       
        test_env = WSGIHandler.generate_env_dict(fake_API_event, 'localhost', 80)
        del(test_env['wsgi.input'])
        del(test_env['wsgi.errors'])
        self.assertEqual(test_env, {'wsgi.version': (1, 0), 'wsgi.url_scheme': 'http', 
                                    'wsgi.multithread': False, 'wsgi.multiprocess': False, 
                                    'wsgi.run_once': False, 'REQUEST_METHOD': 'GET',
                                    'HTTP_TEST': 'test', 'PATH_INFO': '/test',
                                    'SERVER_NAME': 'localhost', 'SERVER_PORT': '80',
                                    'QUERY_STRING': 't=test&t2=test2'})

    def test_wsgi_callback(self):
        test_handler = WSGIHandler(MagicMock(), None, 'localhost', 80, fake_build_response,
                                   fake_error_handler)
        test_handler.wsgi_callback(status='200 OK', response_headers=[('H1', 'Header1'),
                                                                      ('H2', 'Header2')],
                                   exc_info=None)
        self.assertEqual(test_handler.response_status, '200 OK')
        self.assertEqual(test_handler.outbound_headers['H1'], 'Header1')
        self.assertEqual(test_handler.outbound_headers['H2'], 'Header2')
        self.assertEqual(test_handler.outbound_headers['Server'], 'WSGIMagic')

    def test_build_proxy_response(self):
        test_handler = WSGIHandler(MagicMock(), None, 'localhost', 80, fake_build_response,
                                   fake_error_handler)
        test_handler.wsgi_callback(status='200 OK', response_headers=[('H1', 'Header1'),
                                                                      ('H2', 'Header2')],
                                   exc_info=None)
        test_result = test_handler.build_response(test_handler, ['Hello ', 'World'])
        self.assertEqual(test_result['status'], '200')
        self.assertEqual(test_result['headers']['H1'], 'Header1')
        self.assertEqual(test_result['headers']['H2'], 'Header2')
        self.assertEqual(test_result['headers']['Server'], 'WSGIMagic')
        self.assertEqual(test_result['body'], 'Hello World')

    def test_ensure_error_handler_called_when_request_not_processed_correctly(self):
        test_handler = WSGIHandler(MagicMock(), 'This should be a dict', 'localhost', 80,
                                   fake_build_response, fake_error_handler)
        test_handler.wsgi_callback(status='200 OK', response_headers=[('H1', 'Header1'),
                                                                      ('H2', 'Header2')],
                                   exc_info=None)

        test_result = test_handler.build_response(test_handler, [])
        self.assertEqual(test_result, 'You broke it!')


if __name__ == '__main__':
    unittest.main()
