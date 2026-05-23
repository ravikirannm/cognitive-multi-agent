from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
from flask_socketio import SocketIO
from orchestrator import Orchestrator, NOTES_DIR

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

orchestrator = Orchestrator(emit_fn=socketio.emit)


@app.route("/api/status", methods=["GET"])
def status():
    return jsonify({
        "running": orchestrator.is_running,
        "iteration": orchestrator.iteration,
        "latest_note": orchestrator.latest_note,
        "findings": orchestrator.findings,
        "current_step": orchestrator.current_step,
    })


@app.route("/api/start", methods=["POST"])
def start_loop():
    orchestrator.start()
    return jsonify({"message": "Agent loop started."})


@app.route("/api/stop", methods=["POST"])
def stop_loop():
    orchestrator.stop()
    return jsonify({"message": "Agent loop stopped."})


@app.route("/api/step", methods=["POST"])
def step_once():
    result = orchestrator.step()
    return jsonify({"message": "Iteration completed.", "result": result})


@app.route("/api/notes", methods=["GET"])
def list_notes():
    notes = orchestrator.list_notes()
    return jsonify(notes)


@app.route("/api/notes/<path:name>", methods=["GET"])
def get_note(name):
    try:
        content = orchestrator.read_note(name)
        return jsonify({"name": name, "content": content})
    except FileNotFoundError:
        return jsonify({"error": "Note not found."}), 404


@app.route("/api/notes/<path:name>/download", methods=["GET"])
def download_note(name):
    note_path = NOTES_DIR / name
    if not note_path.exists():
        return jsonify({"error": "Note not found."}), 404
    return send_file(str(note_path), as_attachment=True, download_name=name)


@app.route("/api/reset", methods=["POST"])
def reset():
    orchestrator.reset_notes()
    return jsonify({"message": "All notes reset."})
