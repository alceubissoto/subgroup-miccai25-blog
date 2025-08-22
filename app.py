import os
from flask import Flask, render_template
from bokeh.embed import components
from bokeh_app import create_plot

# Create Flask app
app = Flask(__name__)

# Get environment settings
FLASK_ENV = os.environ.get('FLASK_ENV', 'development')
PORT = int(os.environ.get('PORT', 8080))

@app.route('/')
def index():
    # Create the plot directly instead of using a server
    plot = create_plot()
    script, div = components(plot)
    return render_template('index.html', bokeh_script=script, bokeh_div=div)

@app.route('/health')
def health():
    return {'status': 'healthy'}, 200

if __name__ == "__main__":
    # Use host 0.0.0.0 so it's visible inside Docker or on Fly.io
    debug_mode = FLASK_ENV == 'development'
    app.run(host="0.0.0.0", port=FLASK_PORT, debug=debug_mode, use_reloader=False)
