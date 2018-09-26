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
from magic_core import TranslatedRequest, RawResponse, WSGIHandler


def _map_api_gateway_to_request(resource: str, path: str, httpMethod: str, headers: dict,
                                multiValueHeaders: dict, queryStringParameters: dict,
                                multiValueQueryStringParameters: dict, pathParameters: dict,
                                stageVariables: dict, requestContext: dict, body: str,
                                isBase64Encoded: bool, **kwargs):
    """Maps the incoming event from API Gateway to the necessary request structure for our
    application. Note the use of the addition **kwargs in case Amazon adds new fields.
    """
    mapped_headers = {'HTTP_'+key.upper(): value for key, value in headers.items()}
    if multiValueHeaders is not None:
        mapped_headers.update({'HTTP_'+key.upper(): value[0] for key, value in
                               multiValueHeaders.items()})
    request_body = body
    if isBase64Encoded:
        request_body = base64.b64decode(request_body)

    query_string = None
    if len(queryStringParameters) > 0:
        query_string = '&'.join(['{0}={1}'.format(key, value) for key, value
                                 in queryStringParameters.items()])
    if multiValueQueryStringParameters is not None:
        additional_query_string = '&'.join(['{0}={1}'.format(key, value[0]) for key, value
                                 in multiValueQueryStringParameters.items()])
        if query_string is None:
            query_string = additional_query_string
        else:
            query_string += '&' + additional_query_string

    return TranslatedRequest(path, httpMethod, mapped_headers, query_string, request_body)


def _basic_error_handler(exception: Exception) -> dict:
    """This is a basic error handler that just says something went wrong. Make sure your handlers
    have the same signature!
    """
    return {'statusCode': '500',
            'headers': {'Date': datetime.now().strftime("%a, %d %b %Y %H:%M:%S EST"),
                        'Server': 'WSGIMagic'},
            'body': 'Server Error'}


def _build_proxy_response(response: RawResponse, error_handler: callable) -> dict:
    """Once the application completes the request, maps the results into the format required by
    AWS.
    """
    try:
        if response.caught_exception is not None:
            raise response.caught_exception
        message = ''.join([str(message) for message in response.result])

    except Exception as e:
        return error_handler(e)
    return {'statusCode': response.response_status.split(' ')[0],
            'headers': response.outbound_headers,
            'body': message}


def lambda_magic(wsgi_application, additional_response_headers: dict=dict(), server: str='',
                 port: int=0, error_handler=_basic_error_handler, response_modifier: callable=None):
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
        response_modifier: This is an optional callable that you can enter to act on the response
                           from WSGIHandler. Make sure that this function is returning an instance
                           of RawResponse, otherwise the _build_proxy_response function will error.
        """
    def internal(lambda_handler):
        @wraps(lambda_handler)
        def handle(*arg, **kwargs):
            lambda_handler(*arg, **kwargs)
            formatted_request = _map_api_gateway_to_request(**arg[0])
            requester = WSGIHandler(wsgi_application, additional_response_headers, server, port)
            response = requester.handle_request(formatted_request)
            if response_modifier is not None:
                response = response_modifier(response)
            return _build_proxy_response(response, error_handler)
        return handle
    return internal
