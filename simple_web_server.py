import http.server
import os
import socketserver
import sys


def run(web_root='.', port=8080):
    class SimpleHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=web_root, **kwargs)

    with socketserver.TCPServer(("", port), SimpleHTTPRequestHandler) as httpd:
        print(f'Serving at: http://localhost:{httpd.server_address[1]}')
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            httpd.server_close()

if __name__ == '__main__':
    web_root = os.path.dirname(os.path.abspath(sys.argv[0]))
    web_port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    print(f'Starting web server for directory: {web_root}')
    try:
        run(web_root=web_root, port=web_port)
    except Exception as e:
        run(web_root=web_root, port=0)
