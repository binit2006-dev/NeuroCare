# Emergent preview adapter: runs the Flask app under uvicorn. Locally just use `python app.py`.
from a2wsgi import WSGIMiddleware

from app import app as flask_app

app = WSGIMiddleware(flask_app)
