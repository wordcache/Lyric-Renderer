import html
import os
import sys
import threading

import flask
from flask import Flask, request
from flask_socketio import SocketIO, emit, join_room

from lyrics_launcher import run_launcher

app = Flask('lyrics')
socketio = SocketIO(app)


cached_lyrics = {}


def get_lyrics(file):
    file = str(file)
    if file not in cached_lyrics:
        physical_file = os.path.join('.', 'config', 'lyrics', file + '.txt')
        if os.path.isfile(physical_file):
            with open(physical_file) as fp:
                lyrics = ['']
                for line in fp:
                    if not line.strip() and lyrics[-1]:
                        lyrics.append('')
                    else:
                        lyrics[-1] += line
                cached_lyrics[file] = lyrics
        else:
            return []
    return cached_lyrics[file]


def get_lyric(file, paragraph):
    return get_lyrics(file)[paragraph]


def clear_lyrics_cache():
    cached_lyrics = {}


@socketio.on('join controller')
def on_join_controller():
    join_room('controller')


@socketio.on('join')
def on_join_controller():
    join_room('client')


@socketio.on('set server lyrics')
def on_set_lyrics(json):
    file = json['file']
    paragraph = json['paragraph']
    text = get_lyric(file, paragraph)
    text = html.escape(text)
    emit('set client lyrics', {'text': text}, room='client')


@app.route('/list-files')
def list_files():
    return flask.jsonify([html.escape(os.path.splitext(f)[0])
                          for f in os.listdir('./config/lyrics')])


@app.route('/get-file', methods=['GET', 'POST'])
def get_file():
    file = request.args.get('file')
    return flask.jsonify([html.escape(p) for p in get_lyrics(file)])


def ensure_dirs():
    if not os.path.exists('./config/display'):
        import shutil
        os.makedirs('./config/display')
        shutil.copy('data/default.css', './config/display/default.css')
    if not os.path.exists('./config/lyrics'):
        os.makedirs('./config/lyrics')
    if not os.path.exists('./config/backgrounds'):
        os.makedirs('./config/backgrounds')


@app.route('/default.css')
def stylesheet():
    if os.path.isfile('./config/display/default.css'):
        return flask.send_file('./config/display/default.css')
    return ''


@app.route('/')
def client():
    return flask.send_file('data/client.html')


@app.route('/controller')
def controller():
    return flask.send_file('data/controller.html')


def main(have_launcher=True):
    ensure_dirs()
    if have_launcher:
        launcher_thread = threading.Thread(target=run_launcher,
                                           kwargs={
                                               'interrupt_main': True,
                                               'clear_lyrics_cache': clear_lyrics_cache,
                                           },
                                           daemon=True)
        launcher_thread.start()
    socketio.run(app, port=59742)


if __name__ == '__main__':
    main('--no-launcher' not in sys.argv)
