import http.server
import os
import socketserver


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


def start(web_root='.', web_port=8080):
    if not os.path.exists(web_root):
        os.makedirs(web_root, exist_ok=True)
    if os.path.exists(os.path.join(web_root, 'index.html')):
        os.remove(os.path.join(web_root, 'index.html'))
    with open(os.path.join(web_root, 'index.html'), 'w', encoding="utf-8") as f:
        f.write('<html><body><center><h1>Results Overview</h1><p>Please select a result:</p><ul style="list-style-type: none;padding: 0;margin: 0;">')
        for d in sorted(next(os.walk(web_root))[1]):
            f.write(f'<li><a target="_blank" href="{d}/">{d}</a></li>')
        f.write('</ul></center></body></html>')

    print(f'Starting web server for directory: {web_root}')
    try:
        run(web_root=web_root, port=web_port)
    except Exception as e:
        run(web_root=web_root, port=0)
