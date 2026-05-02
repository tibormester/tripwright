from flask import Flask, request, jsonify

app = Flask(__name__)

messages = []


@app.route("/messages", methods=["GET"])
def get_messages():
    return jsonify(messages)


@app.route("/messages", methods=["POST"])
def post_message():
    data = request.get_json()
    if not data or "text" not in data:
        return jsonify({"error": "Missing 'text' field"}), 400
    msg = {"role": data.get("role", "user"), "text": data["text"]}
    messages.append(msg)
    return jsonify(msg), 201


@app.route("/messages", methods=["DELETE"])
def clear_messages():
    messages.clear()
    return jsonify({"status": "cleared"})


if __name__ == "__main__":
    import os
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(debug=debug, port=5000)
