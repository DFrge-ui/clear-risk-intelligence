"""Run the local portfolio with a Windows-compatible WSGI server."""
import argparse
import threading
import webbrowser

from waitress import serve
from clear import create_app


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CLEAR risk portfolio")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--open", action="store_true", help="Open a browser after starting")
    args = parser.parse_args()
    app = create_app()
    address = f"http://127.0.0.1:{args.port}"
    print(f"\nCLEAR is running at {address}\nPress Ctrl+C to stop.\n", flush=True)
    if args.open:
        threading.Timer(1.5, lambda: webbrowser.open(address)).start()
    serve(app, host="127.0.0.1", port=args.port, threads=4)
