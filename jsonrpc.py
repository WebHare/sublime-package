import json
from io import StringIO
import xmlrpc.client

"""
Quick-n-dirty JSON RPC client, adapted from the implementation in
https://github.com/ActiveState/code/blob/master/recipes/Python/552751_JSON_RPC_Server_and_client/recipe-552751.py
"""

class ResponseError(xmlrpc.client.ResponseError):
    pass
class Fault(xmlrpc.client.ResponseError):
    pass

def _get_response(file, sock):
    data = ""
    while 1:
        if sock:
            response = sock.recv(1024)
        else:
            response = file.read(1024)
        if not response:
            break
        data += response

    file.close()

    return data

class Transport(xmlrpc.client.Transport):
    def send_headers(self, connection, headers):
        # change the Content-Type header from 'text/xml' to 'application/json'
        headerdict = dict(headers)
        headerdict["Content-Type"] = "application/json"
        headers = headerdict.items()
        super().send_headers(connection, headers)

    def parse_response(self, response):
        # just return the response, we'll decode later
        return response.read()

class SafeTransport(xmlrpc.client.SafeTransport):
    def send_headers(self, connection, headers):
        # change the Content-Type header from 'text/xml' to 'application/json'
        headerdict = dict(headers)
        headerdict["Content-Type"] = "application/json"
        headers = headerdict.items()
        super().send_headers(connection, headers)

    def parse_response(self, response):
        # just return the response, we'll decode later
        return response.read()

class ServerProxy(object):
    def __init__(self, uri, msg_id=None, transport=None, use_datetime=0):
        # establish a "logical" server connection

        # get the url
        import urllib.request, urllib.parse, urllib.error
        type, uri = urllib.parse.splittype(uri)
        if type not in ("http", "https"):
            raise IOError("unsupported JSON-RPC protocol")
        self.__host, self.__handler = urllib.parse.splithost(uri)
        if not self.__handler:
            self.__handler = "/JSON"

        if transport is None:
            if type == "https":
                transport = SafeTransport(use_datetime=use_datetime)
            else:
                transport = Transport(use_datetime=use_datetime)

        self.__transport = transport
        self.__id        = msg_id

    def __request(self, methodname, params):
        # call a method on the remote server

        request = bytes(json.dumps(dict(id=self.__id, method=methodname,
                                  params=params)), "UTF-8")

        data = self.__transport.request(
            self.__host,
            self.__handler,
            request,
            verbose=False
            )

        response = json.loads(data.decode("UTF-8"))

        if response["id"] != self.__id:
            raise ResponseError("Invalid request id (is: %s, expected: %s)" \
                                % (response["id"], self.__id))
        if response["error"] is not None:
            raise Fault("JSON Error", response["error"])
        return response["result"]

    def __repr__(self):
        return (
            "<ServerProxy for %s%s>" %
            (self.__host, self.__handler)
            )

    __str__ = __repr__

    def __getattr__(self, name):
        # magic method dispatcher
        return xmlrpc.client._Method(self.__request, name)
