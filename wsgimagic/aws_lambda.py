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
from magic_core import TranslatedRequest, WSGIHandler


def _map_api_gateway_to_request(resource: str, path: str, httpMethod: str, headers: dict,
                                queryStringParameters: dict, pathParameters: dict,
                                stageVariables: dict, requestContext: dict, body: str,
                                isBase64Encoded: bool):
    """Maps the incoming event from API Gateway to the necessary request structure for our
    application.
    """
    mapped_headers = {'HTTP_'+key.upper(): value for key, value in headers.items()}
    request_body = body
    if isBase64Encoded:
        request_body = base64.b64decode(request_body)

    query_string = None
    if len(queryStringParameters) > 0:
        query_string = '&'.join(['{0}={1}'.format(key, value) for key, value
                                 in queryStringParameters.items()])

    return TranslatedRequest(path, httpMethod, mapped_headers, query_string, request_body)


def _basic_error_handler(exception: Exception) -> dict:
    """This is a basic error handler that just says something went wrong. Make sure your handlers
    have the same signature!
    """
    return {'statusCode': '500',
            'headers': {'Date': datetime.now().strftime("%a, %d %b %Y %H:%M:%S EST"),
                        'Server': 'WSGIMagic'},
            'body': 'Server Error'}


def _build_proxy_response(self, result: 'iterable') -> dict:
    """Once the application completes the request, maps the results into the format required by
    AWS.
    """
    try:
        if self.caught_exception is not None:
            raise self.caught_exception
        message = ''.join([str(message) for message in result])

    except Exception as e:
        return self.error_handler(e)
    return {'statusCode': self.response_status.split(' ')[0],
            'headers': self.outbound_headers,
            'body': message}


def lambda_magic(wsgi_application, additional_response_headers: dict=dict(), server: str='',
                 port: int=0, error_handler=_basic_error_handler):
    """This is the magical decorator that handles all of your Lambda WSGI application needs!

    Keyword Args:
        wsgi_application: The application that will be fed the wsgi request.
        additional_headers: This is used to pass along any addition headers that you may need to
                            send to the client
        server: The server host name. This is only important if you are using it in your app.
        port: Since we aren't actually going to be binding to a port, this is mildly falsified, but
              us it if you need it!
        error_handler: This is a callable that is used to return server error messages if something
                       goes really wrong. If you are implementing your own, make absolutely sure
                       that your function signature matches that of _basic_error_handler, otherwise
                       you'll fail to send an error, which is very embarrassing.
        """
    def internal(lambda_handler):
        @wraps(lambda_handler)
        def handle(*arg, **kwargs):
            lambda_handler(*arg, **kwargs)
            formatted_request = _map_api_gateway_to_request(**arg[0])
            requester = WSGIHandler(wsgi_application, additional_response_headers, server, port,
                                    _build_proxy_response, error_handler)
            return requester.handle_request(formatted_request)
        return handle
    return internal
