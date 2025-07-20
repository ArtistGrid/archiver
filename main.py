import os
import threading
import time
from flask import Flask, request, Response, abort, redirect
import requests
from urllib.parse import unquote

app = Flask(__name__)

# Globals
lock = threading.Lock()
current_job = None
logs = []  # store logs as list of strings, limited size
MAX_LOG_LINES = 1000  # limit log length


def log(msg):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    entry = f"[{timestamp}] {msg}"
    print(entry)
    with lock:
        logs.append(entry)
        if len(logs) > MAX_LOG_LINES:
            logs.pop(0)


def archive_url(target_url):
    """
    Sends a request to Wayback Machine to archive the target URL.
    """
    log(f"Starting archive request for: {target_url}")
    try:
        save_url = f"https://web.archive.org/save/{target_url}"
        response = requests.get(save_url)
        if response.status_code == 200:
            log(f"Archive request successful for: {target_url}")
            return True
        else:
            log(f"Archive request failed with status {response.status_code} for: {target_url}")
            return False
    except Exception as e:
        log(f"Exception during archive request: {e}")
        return False


def archive_job(target_url, password):
    global current_job
    expected_password = os.getenv("ARCHIVE_PASSWORD")

    log(f"Received archive request for '{target_url}'")

    if password != expected_password:
        log("Password mismatch detected. Aborting archive request.")
        return

    log("Password matched successfully.")
    log("Waiting 10 minutes before archiving...")
    time.sleep(600)

    with lock:
        if current_job != threading.current_thread():
            log("Detected newer archive request. Cancelling this one.")
            return

    success = archive_url(target_url)
    if success:
        log("Archiving process completed successfully.")
    else:
        log("Archiving process failed.")

    with lock:
        current_job = None


@app.route('/')
@app.route('/index.html')
def index():
    # Return logs as white text on black background, monospace
    with lock:
        content = "\n".join(logs[-MAX_LOG_LINES:])
    html = f"""
    <html>
    <head>
        <title>Archive Logs</title>
        <style>
            body {{
                background-color: black;
                color: white;
                font-family: monospace;
                white-space: pre-wrap;
                padding: 20px;
            }}
        </style>
    </head>
    <body>
    {content}
    </body>
    </html>
    """
    return html


@app.route('/archive/<path:url_to_archive>', methods=['GET'])
def archive_endpoint(url_to_archive):
    global current_job

    # URL decode the target URL from the path
    target_url = unquote(url_to_archive)

    # Read password from header (X-Password)
    password = request.headers.get('X-Password', '')

    log(f"Incoming archive request for URL: {target_url}")

    expected_password = os.getenv("ARCHIVE_PASSWORD")
    if not expected_password:
        log("No ARCHIVE_PASSWORD set in environment. Rejecting request.")
        abort(500, "Server configuration error.")

    if password != expected_password:
        log("Password mismatch for archive request.")
        abort(401, "Unauthorized: Password mismatch.")

    with lock:
        if current_job and current_job.is_alive():
            log("Cancelling previous archive job due to new request.")
            # Mark old job as cancelled by clearing current_job,
            # the thread checks and exits if it is not current_job.
            current_job = None

        # Start new archive thread
        t = threading.Thread(target=archive_job, args=(target_url, password))
        current_job = t
        t.start()
        log(f"Started new archive job for: {target_url}")

    return f"Archive request for {target_url} accepted. Archiving will start after 10 minutes if no newer request is received.\n", 202


if __name__ == '__main__':
    log("Starting Archive Server...")
    app.run(host='0.0.0.0', port=8080)
