import unittest
from unittest.mock import MagicMock
import os
import sys


lib_dir = os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')), 'wsgimagic')
if lib_dir not in sys.path:
    sys.path.insert(1, lib_dir)

from magic_core import WSGIHandler, TranslatedRequest, RawResponse


fake_API_event = TranslatedRequest('/test', 'GET', {'HTTP_TEST': 'test'}, 't=test&t2=test2',
                                   'hello')


class FakeWSGIApp:
    pass


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
        test_handler = WSGIHandler(MagicMock(), None, 'localhost', 80)
        test_handler.wsgi_callback(status='200 OK', response_headers=[('H1', 'Header1'),
                                                                      ('H2', 'Header2')],
                                   exc_info=None)
        self.assertEqual(test_handler.response.response_status, '200 OK')
        self.assertEqual(test_handler.response.outbound_headers['H1'], 'Header1')
        self.assertEqual(test_handler.response.outbound_headers['H2'], 'Header2')
        self.assertEqual(test_handler.response.outbound_headers['Server'], 'WSGIMagic')


if __name__ == '__main__':
    unittest.main()
