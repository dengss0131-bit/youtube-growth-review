from src.app import Handler, HOST, PORT
from http.server import ThreadingHTTPServer

if __name__ == "__main__":
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"New-media growth review server running at http://{HOST}:{PORT}", flush=True)
    server.serve_forever()
