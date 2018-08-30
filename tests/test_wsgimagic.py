import unittest
from unittest.mock import MagicMock
from flask import Flask, request

app = Flask(__name__)


@app.route('/hello', methods=['POST'])
def hello():
    #print(request.headers['Authorization'])
    return str(request.headers['Authorization'])


fake_event = {
    "resource": None,
    "path": '/hello',
    "httpMethod": 'GET',
    "headers": {"Authorization": "Bearer HI"},
    "queryStringParameters": {'test1': 'value1', 'test2': 'value2'},
    "pathParameters":  {},
    "stageVariables": {},
    "requestContext": {},
    "body": "who am i",
    "isBase64Encoded": False
}


@wsgi_magic(app, {'Test': 'Response'})
def handler(event, context):
    print(event)
    print('Handled')