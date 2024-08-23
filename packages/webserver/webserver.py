import http.server
import os
import socketserver


def run(web_root='.', port=8080):
    class SimpleHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=web_root, **kwargs)

    class StoppableHTTPServer(http.server.HTTPServer):
        def run(self):
            try:
                self.serve_forever()
            except KeyboardInterrupt:
                pass
            finally:
                # Clean-up server (close socket, etc.)
                self.server_close()

    if os.path.exists(os.path.join(web_root, 'index.html')):
        os.remove(os.path.join(web_root, 'index.html'))
    with open(os.path.join(web_root, 'index.html'), 'w', encoding="utf-8") as f:
        f.write('<html><body><center><h1>Results Overview</h1><p>Please select a result:</p><ul style="list-style-type: none;padding: 0;margin: 0;">')
        for d in sorted(next(os.walk(web_root))[1]):
            f.write(f'<li><a target="_blank" href="{d}/">{d}</a></li>')
        f.write('</ul></center></body></html>')

    with socketserver.TCPServer(("", port), SimpleHTTPRequestHandler) as httpd:
        print("Serving at port", port)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            # Clean-up server (close socket, etc.)
            httpd.server_close()
