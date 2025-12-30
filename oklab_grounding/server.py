"""
HTTP service wrapper for the grounding framework.

Provides REST API endpoints for grounding operations, allowing other languages
to use the framework via HTTP calls.
"""

from flask import Flask, request, jsonify
from typing import Dict, Any
import json
from .space import Grounding, Symbol
from .oklab import OKLabSpace, OKLab, SphericalRegion
from .cgir import CGIRBuilder
from .verification import verify_oklab_consistency

app = Flask(__name__)

# Global state for demonstration
# In production, this would be proper session/state management
_spaces: Dict[str, OKLabSpace] = {}
_groundings: Dict[str, Grounding] = {}

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({"status": "ok", "service": "oklab-grounding-server"})

@app.route('/spaces/oklab', methods=['POST'])
def create_space():
    """Create a new OKLab space."""
    space_id = request.json.get('id', 'default')
    space = OKLabSpace()
    _spaces[space_id] = space
    return jsonify({"space_id": space_id, "status": "created"})

@app.route('/spaces/<space_id>/groundings', methods=['POST'])
def create_grounding(space_id: str):
    """Create a new grounding for a space."""
    if space_id not in _spaces:
        return jsonify({"error": f"Space {space_id} not found"}), 404

    grounding_id = request.json.get('id', 'default')
    grounding = Grounding(_spaces[space_id])
    _groundings[grounding_id] = grounding
    return jsonify({"grounding_id": grounding_id, "status": "created"})

@app.route('/groundings/<grounding_id>/bind', methods=['POST'])
def bind_symbol(grounding_id: str):
    """Bind a symbol to a region in the grounding."""
    if grounding_id not in _groundings:
        return jsonify({"error": f"Grounding {grounding_id} not found"}), 404

    data = request.json
    symbol = data['symbol']
    region_data = data['region']

    # Create region from data (simple spherical region for now)
    center = OKLab(**region_data['center'])
    radius = region_data.get('radius', 0.1)
    region = SphericalRegion(center, radius, _groundings[grounding_id].space)

    _groundings[grounding_id].bind_region(symbol, region)
    return jsonify({"status": "bound", "symbol": symbol})

@app.route('/groundings/<grounding_id>/query/nearest', methods=['POST'])
def query_nearest(grounding_id: str):
    """Find the nearest symbol to a given point."""
    if grounding_id not in _groundings:
        return jsonify({"error": f"Grounding {grounding_id} not found"}), 404

    data = request.json
    point = OKLab(**data['point'])

    nearest = _groundings[grounding_id].nearest_symbol(point)
    return jsonify({"nearest_symbol": nearest})

@app.route('/spaces/oklab/mix', methods=['POST'])
def mix_colors():
    """Perform color mixing operation."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400

        colors_data = data.get('colors')
        if not colors_data or not isinstance(colors_data, list):
            return jsonify({"error": "colors must be a non-empty list"}), 400

        weights = data.get('weights')
        if weights and not isinstance(weights, list):
            return jsonify({"error": "weights must be a list or omitted"}), 400

        # Validate color data
        colors = []
        for i, c in enumerate(colors_data):
            try:
                if not isinstance(c, dict) or 'L' not in c or 'a' not in c or 'b' not in c:
                    return jsonify({"error": f"color {i} must have L, a, b fields"}), 400
                color = OKLab(c['L'], c['a'], c['b'])
                colors.append(color)
            except Exception as e:
                return jsonify({"error": f"Invalid color data for color {i}: {str(e)}"}), 400

        space = OKLabSpace()
        result = space.mix(colors, weights or [])

        return jsonify({
            "result": {"L": result.L, "a": result.a, "b": result.b}
        })

    except Exception as e:
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500

@app.route('/cgir/simulate', methods=['POST'])
def simulate_cgir():
    """Load and simulate a CGIR."""
    data = request.json
    cgir_data = data['cgir']
    steps = data.get('steps', 100)

    # Parse CGIR
    if isinstance(cgir_data, str):
        cgir_data = json.loads(cgir_data)

    builder = CGIRBuilder.from_dict(cgir_data)
    trajectory = builder.simulate(steps)

    return jsonify({"trajectory": trajectory})

@app.route('/spaces/oklab/verify', methods=['POST'])
def verify_space():
    """Verify OKLab space consistency."""
    data = request.json
    colors_data = data.get('colors', [])

    colors = [OKLab(**c) for c in colors_data]
    space = OKLabSpace()

    try:
        verify_oklab_consistency(space, colors)
        return jsonify({"status": "verified", "message": "All properties hold"})
    except Exception as e:
        return jsonify({"status": "failed", "error": str(e)}), 400

@app.errorhandler(400)
def bad_request(error):
    return jsonify({"error": "Bad request", "message": str(error)}), 400

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not found", "message": str(error)}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error", "message": str(error)}), 500

def run_server(host: str = '0.0.0.0', port: int = 8000, debug: bool = False):
    """Run the grounding server."""
    app.run(host=host, port=port, debug=debug)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='OKLab Grounding Server')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=8000, help='Port to bind to')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    args = parser.parse_args()

    run_server(host=args.host, port=args.port, debug=args.debug)