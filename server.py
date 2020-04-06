# -*- coding: utf-8 -*-

import json
import socket
from email.message import Message
from email.parser import Parser
from functools import lru_cache
from io import BufferedReader
from typing import BinaryIO, Tuple
from urllib.parse import urlparse, ParseResult

from logger import get_logger
from oxr_client import OXRClient
from settings import HOST, PORT, NAME, OXR_KEY

MAX_LINE = 64 * 1024
MAX_HEADERS = 100
LOGGER = get_logger('server')


class HTTPServer:
    def __init__(self, host: str, port: int, server_name: str) -> None:
        self._host = host
        self._port = port
        self._server_name = server_name
        self._oxr_client = OXRClient(app_id=OXR_KEY)

    @staticmethod
    def raise_and_log(status: int, reason: str, body: str = None) -> None:
        LOGGER.error(body if body else reason)
        raise HTTPError(status, reason, body)

    def serve_forever(self) -> None:
        serv_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, proto=0)

        try:
            serv_sock.bind((self._host, self._port))
            serv_sock.listen()

            LOGGER.info(f'Run server {self._server_name} on {self._host}:{self._port}')

            while True:
                conn, _ = serv_sock.accept()
                try:
                    self.serve_client(conn)
                except Exception as e:
                    LOGGER.error('Client serving failed', e)
        finally:
            serv_sock.close()

    def serve_client(self, conn: socket.socket) -> None:
        try:
            req = self.parse_request(conn)
            resp = self.handle_request(req)
            self.send_response(conn, resp)
        except ConnectionResetError:
            conn = None
        except Exception as e:
            self.send_error(conn, e)

        if conn:
            req.rfile.close()
            conn.close()

    def parse_request(self, conn: socket) -> 'Request':
        LOGGER.info(f'Parsing request from {conn.getpeername()}...')
        rfile = conn.makefile('rb')
        method, target, ver = self.parse_request_line(rfile)
        headers = self.parse_headers(rfile)
        host = headers.get('Host')
        if not host:
            self.raise_and_log(400, 'Bad request', 'Host header is missing')
        if host not in (self._server_name, f'{self._server_name}:{self._port}'):
            self.raise_and_log(404, 'Not found', 'Invalid host')
        return Request(method, target, ver, headers, rfile)

    def parse_request_line(self, rfile: BinaryIO) -> Tuple[str, str, str]:
        raw = rfile.readline(MAX_LINE + 1)
        if len(raw) > MAX_LINE:
            self.raise_and_log(400, 'Bad request', 'Request line is too long')

        req_line = str(raw, 'iso-8859-1')
        words = req_line.split()
        if len(words) != 3:
            self.raise_and_log(400, 'Bad request', 'Malformed request line')

        method, target, ver = words
        if ver != 'HTTP/1.1':
            self.raise_and_log(505, 'HTTP Version Not Supported')
        return method, target, ver

    def parse_headers(self, rfile: BinaryIO) -> Message:
        headers = []
        while True:
            line = rfile.readline(MAX_LINE + 1)
            if len(line) > MAX_LINE:
                self.raise_and_log(494, 'Request header too large')

            if line in (b'\r\n', b'\n', b''):
                break

            headers.append(line)
            if len(headers) > MAX_HEADERS:
                raise HTTPError(494, 'Too many headers')

        sheaders = b''.join(headers).decode('iso-8859-1')
        return Parser().parsestr(sheaders)

    def handle_request(self, req: 'Request') -> 'Response':
        LOGGER.info('Handling request...')
        if req.path.startswith('/convert/') and req.method == 'GET':
            amount = req.path[len('/convert/'):]
            try:
                amount = float(amount)
            except ValueError:
                self.raise_and_log(404, 'Bad request', 'Amount value must be float')
            return self.handle_get_convert(req, amount)

        raise HTTPError(404, 'Not found')

    def send_response(self, conn: socket.socket, resp: 'Response') -> None:
        with conn.makefile('wb') as wfile:
            status_line = f'HTTP/1.1 {resp.status} {resp.reason}\r\n'
            wfile.write(status_line.encode('iso-8859-1'))

            if resp.headers:
                for (key, value) in resp.headers:
                    header_line = f'{key}: {value}\r\n'
                    wfile.write(header_line.encode('iso-8859-1'))

            wfile.write(b'\r\n')

            if resp.body:
                wfile.write(resp.body)

    def send_error(self, conn: socket.socket, err: 'HTTPError') -> None:
        try:
            status = err.status
            reason = err.reason
            body = (err.body or err.reason).encode('utf-8')
        except:
            status = 500
            reason = b'Internal Server Error'
            body = b'Internal Server Error'
        resp = Response(status, reason, [('Content-Length', len(body))], body)
        self.send_response(conn, resp)

    def handle_get_convert(self, req: 'Request', amount: float) -> 'Response':
        accept = req.headers.get('Accept')
        if 'application/json' in accept or '*/*' in accept:
            content_type = 'application/json; charset=utf-8'
            res = self._oxr_client.get_latest(symbols=['RUB'])
            target_currency = next(iter(res['rates']))

            body = json.dumps({
                'timestamp': res['timestamp'],
                'base_currency': res['base'],
                'base_amount': amount,
                'target_currency': target_currency,
                'target_amount': res['rates'][target_currency] * amount
            })
        else:
            LOGGER.error('Bad content type')
            return Response(406, 'Not Acceptable')

        body = body.encode('utf-8')
        headers = [('Content-Type', content_type),
                   ('Content-Length', len(body))]

        LOGGER.info('Success!')
        return Response(200, 'OK', headers, body)


class Request:
    def __init__(self, method: str, target: str, version: str, headers: Message, rfile: BufferedReader) -> None:
        self.method = method
        self.target = target
        self.version = version
        self.headers = headers
        self.rfile = rfile

    @property
    def path(self) -> str:
        return self.url.path

    @property
    @lru_cache(maxsize=None)
    def url(self) -> ParseResult:
        return urlparse(self.target)


class Response:
    def __init__(self, status: int, reason: str, headers: list = None, body: bytes = None) -> None:
        self.status = status
        self.reason = reason
        self.headers = headers
        self.body = body


class HTTPError(Exception):
    def __init__(self, status: int, reason: str, body: str = None) -> None:
        super()
        self.status = status
        self.reason = reason
        self.body = body


if __name__ == '__main__':
    serv = HTTPServer(HOST, PORT, NAME)
    try:
        serv.serve_forever()
    except KeyboardInterrupt:
        pass
