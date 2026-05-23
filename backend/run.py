import eventlet
eventlet.monkey_patch()

from app import socketio, app  # noqa: E402 — must come after monkey_patch

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)
