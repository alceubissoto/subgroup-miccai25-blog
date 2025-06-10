from flask import Flask, render_template, url_for
from threading import Thread
from bokeh.server.server import Server
from bokeh.embed import server_document
from bokeh_app import modify_doc

# Create Flask app
app = Flask(__name__)

def bk_worker():
    server = Server(
        {'/bkapp': modify_doc},
        port=5100,  # <---- use a free port here!
        allow_websocket_origin=[
            "localhost:9000",
            "127.0.0.1:9000",
            # "your.fly.io.app" (when deploying)
        ]
    )
    server.start()
    server.io_loop.start()

# Start Bokeh server in the background (daemon thread)
Thread(target=bk_worker, daemon=True).start()

@app.route('/')
def index():
    script = server_document('http://localhost:5100/bkapp')
    return render_template('index.html', bokeh_script=script)

if __name__ == "__main__":
    # Use host 0.0.0.0 so it's visible inside Docker or on Fly.io
    app.run(host="0.0.0.0", port=9000, debug=False, use_reloader=False)
