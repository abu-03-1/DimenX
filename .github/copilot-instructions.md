## Quick orientation

This repo implements a simple 2D -> 3D web service: a Flask backend that
runs a MiDaS depth estimator and converts depth maps into a GLB mesh, and a
small static frontend (Three.js) that uploads an image and previews the GLB.

Key files/directories
- `app.py` — Flask app and HTTP endpoints. Note: the file loads the MiDaS
  model at module import time and exposes `/upload`, `/models/<name>`, and
  `/download/<name>`.
- `model_utils.py` — model loading (`load_midas`), `estimate_depth`, and
  `depth_to_mesh` (Open3D + trimesh pipeline that exports `.glb`).
- `uploads/` — temporary uploaded images. `models/` — generated `.glb` files.
- `static/` — frontend: `index.html`, `script.js` (POSTs to `/upload`),
  `style.css`. Frontend uses Three.js + GLTFLoader to display models.
- `requirements.txt` — project dependencies (torch, open3d, trimesh, pygltflib, etc.).

Important behaviours / conventions for code edits
- The MiDaS model is loaded once at module import in `app.py` (see the
  top-level `load_midas(...)` call). Keep heavy model initialization at
  module level to avoid reloading per-request.
- The upload handler expects a multipart form field named `image` and
  responds with JSON: `{ "model_url": "/models/<name>.glb", "download_url": "/download/<name>.glb" }`.
- Output meshes are written to `models/` using `trimesh.Trimesh.export(out_path)`
  (format `.glb`). Filenames are sanitized with `secure_filename` fallback.
- Allowed image extensions: `png`, `jpg`, `jpeg` (see `ALLOWED_EXT` in `app.py`).

Notable code quirk to be aware of
- `app.py` currently contains two `Flask(__name__, ...)` assignments; the
  later one overrides the earlier. When changing static paths or app
  configuration, prefer the bottom-most `app = Flask(...)` instance.

Dev / run instructions (discoverable and tested locally)
- Create and activate a virtualenv, then install deps:

  ```powershell
  python -m venv .venv; .\.venv\Scripts\Activate.ps1; python -m pip install -r requirements.txt
  ```

- Run locally (development):

  ```powershell
  python app.py
  ```

- Note on GPU: `model_utils.load_midas`/`app.py` currently uses `device='cpu'`.
  To use CUDA, ensure PyTorch with CUDA is installed and set `device='cuda'`.

API examples (useful snippets for code changes / tests)
- Upload an image (client): Form key `image` -> POST `/upload` => JSON
  containing `model_url` and `download_url`. `script.js` shows the exact
  fetch usage — mirror that when writing tests or helper scripts.

Integration and edges observed from code
- Mesh pipeline: Poisson reconstruction is attempted first; fallback uses
  Ball Pivoting. Simplification target is ~20k triangles. Expect long
  processing times for large images and potential OOM on GPU for large
  resolutions.
- The server returns a direct static URL (`/models/<name>`) — CI or
  deployment should ensure `models/` is persisted/served by the host.

Editing guidelines for an AI agent
- When modifying inference code: keep model loading at import time.
- If you add async/background jobs, ensure `uploads/` and `models/` are
  properly synchronized (current code is synchronous and blocking).
- When changing endpoints, update `static/script.js` accordingly — the
  JS client expects the response shape shown above.

What I couldn't infer (ask dev)
- Intended deployment: should `models/` be stored on disk, S3, or served
  by a separate static host? (Current code serves from local disk.)
- Any max upload size, auth, or rate limits expected in production?

If this is helpful I can iterate — e.g. add a short checklist for
performance tuning (image resizing, batching), or prepare a small
integration test that posts an image and validates a `.glb` was produced.
