# tripwright
ai powered storytelling engine designed to boost booking conversions by selling a vivid experience. Going beyond just agents and a harness that burn through compute, but towards an engine that deliberately leverages ai where and when needed.

## Getting started

### Backend (Python Flask)

```bash
cd backend
pip install -r requirements.txt
python app.py
```

The API runs on `http://localhost:5000`.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/messages` | Fetch all messages |
| POST | `/messages` | Add a message `{"role": "user", "text": "..."}` |
| DELETE | `/messages` | Clear all messages |

### Client (Node.js CLI)

```bash
cd client
node client.js
```

Type a message and press Enter to send it to the backend. Built-in commands:

- `/history` — print all stored messages
- `/clear` — delete all messages
- `/quit` — exit

Set `API_URL` environment variable to point at a different backend address (default: `http://localhost:5000`).

