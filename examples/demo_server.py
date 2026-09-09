import json
import os
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from typing import Any
from urllib.parse import urlsplit


class DemoRequestHandler(BaseHTTPRequestHandler):
    server_version = "ApiTestDemo/1.0"

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _json_body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            return json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return {}

    def _send(self, status: int, body: dict[str, Any]) -> None:
        payload = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _authorized(self) -> bool:
        return self.headers.get("Authorization") == "Bearer demo-token"

    def do_POST(self) -> None:
        if self.path != "/login":
            self._send(404, {"code": 404, "msg": "not found"})
            return
        body = self._json_body()
        if body.get("username") == "admin" and body.get("password") == "123456":
            self._send(
                200,
                {
                    "code": 0,
                    "msg": "登录成功",
                    "data": {"token": "demo-token", "user": {"id": 1}},
                },
            )
            return
        self._send(401, {"code": 401, "msg": "登录失败"})

    def do_GET(self) -> None:
        if not self._authorized():
            self._send(401, {"code": 401, "msg": "未授权"})
            return
        request_path = urlsplit(self.path).path
        if request_path == "/users":
            self._send(200, {"code": 0, "msg": "获取用户列表成功", "data": [{"id": 1, "name": "admin"}]})
            return
        if re.fullmatch(r"/users/\d+", request_path):
            user_id = int(request_path.rsplit("/", 1)[-1])
            self._send(200, {"code": 0, "msg": "获取用户成功", "data": {"id": user_id, "name": "admin"}})
            return
        self._send(404, {"code": 404, "msg": "not found"})

    def do_PUT(self) -> None:
        if not self._authorized():
            self._send(401, {"code": 401, "msg": "未授权"})
            return
        match = re.fullmatch(r"/users/(\d+)/state", urlsplit(self.path).path)
        if not match:
            self._send(404, {"code": 404, "msg": "not found"})
            return
        body = self._json_body()
        self._send(
            200,
            {
                "code": 0,
                "msg": "设置状态成功",
                "data": {"id": int(match.group(1)), "state": body.get("state")},
            },
        )


def create_demo_server(host: str = "127.0.0.1", port: int = 0) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer((host, port), DemoRequestHandler)
    server.url = f"http://{server.server_address[0]}:{server.server_address[1]}"  # type: ignore[attr-defined]
    return server


if __name__ == "__main__":
    demo_server = create_demo_server(
        host=os.getenv("DEMO_HOST", "127.0.0.1"),
        port=int(os.getenv("DEMO_PORT", "0")),
    )
    print(f"Demo API server started at {demo_server.url}")  # type: ignore[attr-defined]
    thread = Thread(target=demo_server.serve_forever, daemon=True)
    thread.start()
    try:
        thread.join()
    except KeyboardInterrupt:
        demo_server.shutdown()
