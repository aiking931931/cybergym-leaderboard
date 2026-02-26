#!/usr/bin/env python3
import json
import os
import signal
import subprocess
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

TIMEOUT = os.getenv("TIMEOUT", "10s")
EXECUTOR_COMMAND = os.getenv("EXECUTOR_COMMAND")
PORT = int(os.getenv("PORT", "1337"))
HOST = os.getenv("HOST", "0.0.0.0")
TEMP_FILE = "/tmp/proof_of_concept"
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


class ProofOfConceptHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Health check endpoint
        parsed_path = urlparse(self.path)
        if parsed_path.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            health_response = {"status": "healthy"}
            self.wfile.write(json.dumps(health_response).encode())
        else:
            self.send_error_response(404, "Not Found")

    def do_POST(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length > MAX_FILE_SIZE:
                self.send_error_response(413, "File size exceeds the maximum limit of 10 MB")
                return

            with open(TEMP_FILE, "wb") as f:
                f.write(self.rfile.read(content_length))

            # Run the executor command with the temp file as argument
            if EXECUTOR_COMMAND is None:
                self.send_error_response(500, "EXECUTOR_COMMAND not configured")
                return
            result = subprocess.run(
                ["timeout", "-s", "SIGKILL", TIMEOUT, EXECUTOR_COMMAND],
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )

            # Check if process was killed by SIGKILL (128 + signal number)
            if result.returncode == 128 + signal.SIGKILL:
                self.send_error_response(504, "Request timed out")
                return

            # Prepare the JSON response
            response = {
                "exit_code": result.returncode,
                "output": result.stdout.decode(errors="replace"),
            }

            # Send successful response
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response, sort_keys=True).encode())

        except Exception as e:
            self.send_error_response(500, str(e))

    def send_error_response(self, status_code, message):
        error_response = {
            "status": "error",
            "message": message,
        }
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(error_response).encode())

    def log_message(self, format, *args):
        # Override to customize logging
        print("{} - {}".format(self.address_string(), format % args))


def main():
    server = HTTPServer((HOST, PORT), ProofOfConceptHandler)
    print("HTTP server listening on port %d..." % PORT)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        server.shutdown()


if __name__ == "__main__":
    main()
