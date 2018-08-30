"""wsgimagic is designed to allow you to effortlessly transition any WSGI compliant Python application
(eg Flask, Django) to a completely serverless architecture using an AWS APIGateway Lambda Proxy pointing to a Lambda
function running your code. By simply using the wsgi_magic decorator, you can pass the incoming request off to your
application and ensure that the values are returned in the required format.
"""

import sys
from io import StringIO
from datetime import datetime
from functools import wraps
import base64

class _APIGatewayEvent:
    """Turns the incoming Lambda event dictionary into something easily usable by our applications."""
    def __init__(self, resource: str, path: str, httpMethod: str, headers: dict,
                 queryStringParameters: dict, pathParameters: dict, stageVariables: dict,
                 requestContext: dict, body: str, isBase64Encoded: bool):
        """Set the instance variables and do the mappings for headers and possible decoding of the request body"""
        self.resource = resource
        self.path = path
        self.http_method = httpMethod
        self.headers = {'HTTP_'+key.upper(): value for key, value in headers.items()}
        self.query_string_parameters = queryStringParameters
        self.path_parameters = pathParameters
        self.stage_variables = stageVariables
        self.request_context = requestContext
        self.is_base_64_encoded = isBase64Encoded
        if self.is_base_64_encoded:
            self.body = base64.b64decode(body)
        else:
            self.body = body


def _basic_error_handler(exception: Exception) -> dict:
    """This is a basic error handler that just says something went wrong. Make sure your handlers have the same
    signature!
    """
    return {'statusCode': '500',
            'headers': {'Date': datetime.now().strftime("%a, %d %b %Y %H:%M:%S EST"), 'Server': 'WSGIMagic'},
            'body': 'Server Error'}


class _WSGIHandler:
    """This class performs the heavy lifting of translating incoming requests and returning responses."""

    def __init__(self, wsgi_application: 'WSGI Application', additional_response_headers: dict, server: str, port: int,
                 error_handler: callable):
        """ Initializer for the _WSGIHandler class.

        Keyword Args:
        wsgi_application: The application that will be fed the wsgi request.
        additional_headers: This is used to pass along any addition headers that you may need to send to the client
        server: The server host name. This is only important if you are using it in your app.
        port: Since we aren't actually going to be binding to a port, this is mildly falsified, but us it if you need it!
        error_handler: This is a callable that is used to return server error messages if something goes really wrong.
                   If you are implementing your own, make absolutely sure that your function signature matches that of
                   _basic_error_handler, otherwise you'll fail to send an error, which is very embarrassing.
        """

        self.app = wsgi_application
        self.additional_response_headers = additional_response_headers
        self.server = server
        self.port = port
        self.error_handler = error_handler
        self.caught_exception = None
        self.response_status = None
        self.outbound_headers = dict()

    @staticmethod
    def generate_env_dict(request: _APIGatewayEvent, server: str, port: int) -> dict:
        """Builds the necessary WSGI environment based on the incoming request"""
        environment = dict()

        environment['wsgi.version'] = (1, 0)
        environment['wsgi.url_scheme'] = 'http'
        environment['wsgi.input'] = StringIO(request.body)
        environment['wsgi.errors'] = sys.stderr
        environment['wsgi.multithread'] = False
        environment['wsgi.multiprocess'] = False
        environment['wsgi.run_once'] = False
        environment['REQUEST_METHOD'] = request.http_method
        environment['PATH_INFO'] = request.path
        environment['SERVER_NAME'] = server
        environment['SERVER_PORT'] = str(port)
        if request.query_string_parameters is not None:
            environment['QUERY_STRING'] = '&'.join(['{0}={1}'.format(key, value) for key, value
                                            in request.query_string_parameters.items()])
        else:
            environment['QUERY_STRING'] = ''
        environment.update(request.headers)
        return environment

    def wsgi_callback(self, status: str, response_headers: [()], exc_info=None) -> None:
        """This is used as the start response function that is sent to the application."""
        try:
            if exc_info is not None:
                raise(exc_info[0], exc_info[1], exc_info[2])
            response_header_dict = {tup[0]: tup[1] for tup in response_headers}
            response_header_dict.update(self.additional_response_headers)
            response_header_dict.update({'Date': datetime.now().strftime("%a, %d %b %Y %H:%M:%S EST"),
                                         'Server': 'WSGIMagic'})
            self.response_status = status
            self.outbound_headers = response_header_dict

        except Exception as e:
            self.caught_exception = e

    def build_proxy_response(self, result: 'iterable') -> dict:
        """Once the application completes the request, maps the results into the format required by AWS."""
        try:
            if self.caught_exception is not None:
                raise self.caught_exception
            message = ''.join([str(message) for message in result])

        except Exception as e:
            return self.error_handler(e)
        return {'statusCode': self.response_status.split(' ')[0], 'headers': self.outbound_headers, 'body': message}

    def handle_request(self, request: _APIGatewayEvent) -> dict:
        result = self.app(self.generate_env_dict(request, self.server, self.port), self.wsgi_callback)
        return self.build_proxy_response(result)


def wsgi_magic(wsgi_application, additional_response_headers: dict=dict(), server: str='', port: int=0,
               error_handler=_basic_error_handler):
    """This is the magical decorator that handles all of your WSGI application needs!

    Keyword Args:
        wsgi_application: The application that will be fed the wsgi request.
        additional_headers: This is used to pass along any addition headers that you may need to send to the client
        server: The server host name. This is only important if you are using it in your app.
        port: Since we aren't actually going to be binding to a port, this is mildly falsified, but us it if you need it!
        error_handler: This is a callable that is used to return server error messages if something goes really wrong.
                   If you are implementing your own, make absolutely sure that your function signature matches that of
                   _basic_error_handler, otherwise you'll fail to send an error, which is very embarrassing.
        """
    def internal(func):
        @wraps(func)
        def handle(*arg, **kwargs):
            func(*arg, **kwargs)
            formatted_request = _APIGatewayEvent(**arg[0])
            requester = _WSGIHandler(wsgi_application, additional_response_headers, server, port, error_handler)
            return requester.handle_request(formatted_request)
        return handle
    return internal
