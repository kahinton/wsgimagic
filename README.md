Welcome to WSGIMagic!

The use of API Gateways backed by Serverless functions is currently expanding at a massive rate, however every provider 
has their own special way of presenting the HTTP request to the backend. This means a lot of very boring, very tedious 
work for us developers every time we want to use a new service. The goal of this package is to remove the barrier between 
the different cloud providers, and allow you to focus on wrting good old Python WSGI APIs.

The first environment that has been targeted is the combination of the AWS API Gateway ending as a proxy to AWS Lambda. 
Before you would need to find out how Amazon was structuring the incoming request information, and how to send that 
informaton back to get a proper response to the client. WSGIMagic allows you to handle everything with a basic decorator. 
The following example illustrates a very small example using Flask.

from flask import Flask

from wsgimagic.aws_lambda import lambda_magic


app = Flask(__name__)


@app.route('/hello', allowed_methods=['GET'])
def hello()
    return 'Hello World'
    

@lambda_magic(app)
def event_handler(event, context):
    pass
    
    
By using the lambda_magic decorator, the incoming API Gateway event will automatically be translated to the WSGI format 
and passed off to your application. For basic request handling, this is all you need to do. The lambda_magic decorator 
also allows you to specify additional response headers that need to be added, define the server name and port that your 
app will be told it is running under, and provide a custom error handler in case something goes really wrong with your 
requests. I will add more written documentation in the near future, however all of the functions should have decent doc 
strings that will provide any other available features.

Long term this package will aim to provide similar decorators for other Serverless providers who also do not pass HTTP 
messages along pre-translated to the WSGI format.
