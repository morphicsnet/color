"""
CLI entry point for the OKLab grounding server.
"""

import argparse
from .server import run_server

def main():
    parser = argparse.ArgumentParser(description='OKLab Grounding Server')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=8000, help='Port to bind to')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    args = parser.parse_args()

    print(f"Starting OKLab Grounding Server on {args.host}:{args.port}")
    run_server(host=args.host, port=args.port, debug=args.debug)

if __name__ == '__main__':
    main()