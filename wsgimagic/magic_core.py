import sys
from io import StringIO
from datetime import datetime as dt


class TranslatedRequest:
    """All sub modules should translate their incoming request object into this form to be passed
    off to the WSGIHandler.
    """
    def __init__(self, path: str, http_method: str, headers: dict, query_string: str,
                 body: str):
        self.path = path
        self.http_method = http_method
        self.headers = headers
        self.query_string= query_string
        self.body = body


class RawResponse:
    """All submodules should expect to receive an instance of this class back from the
    handle_response method of the WSGIHandler. all outgoing response mappers can then be designed to
    build from this.
    """
    def __init__(self):
        self.result: 'iterable' = None
        self.caught_exception: Exception = None
        self.response_status: str = None
        self.outbound_headers: dict = dict()


class WSGIHandler:
    """This class performs the heavy lifting of translating incoming requests and returning
    responses.
    """

    def __init__(self, wsgi_application: 'WSGI Application', additional_response_headers: dict,
                 server: str, port: int):
        """ Initializer for the WSGIHandler class.

        Keyword Args:
        wsgi_application: The application that will be fed the wsgi request.
        additional_headers: This is used to pass along any addition headers that you may need to
                            send to the client
        server: The server host name. This is only important if you are using it in your app.
        port: Since we aren't actually going to be binding to a port, this is mildly falsified, but
              use it if you need it!
        """

        self.app = wsgi_application
        self.additional_response_headers = additional_response_headers
        self.server = server
        self.port = port
        self.response = RawResponse()

    @staticmethod
    def generate_env_dict(request: TranslatedRequest, server: str, port: int) -> dict:
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
        if request.query_string is not None:
            environment['QUERY_STRING'] = request.query_string
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
            if self.additional_response_headers is not None:
                response_header_dict.update(self.additional_response_headers)
            response_header_dict.update({'Date': dt.now().strftime("%a, %d %b %Y %H:%M:%S EST"),
                                         'Server': 'WSGIMagic'})
            self.response.response_status = status
            self.response.outbound_headers = response_header_dict

        except Exception as e:
            self.response.caught_exception = e

    def handle_request(self, request: TranslatedRequest) -> RawResponse:
        self.response.result = self.app(self.generate_env_dict(request, self.server, self.port),
                                        self.wsgi_callback)
        return self.response
