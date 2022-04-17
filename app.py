import os
import time

from AutoDanmuGen.config import Config
from AutoDanmuGen.core.prepare import Preparer
from AutoDanmuGen.core.extract import Extractor
from flask import (
    Flask,
    jsonify,
    redirect,
    render_template,
    request,
    url_for
)


app = Flask(__name__)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/video')
def show_video():
    video_name = request.args['video_name']
    comment_name = request.args['comment_name']
    _id = comment_name[comment_name.find('_') + 1: comment_name.find('.')]
    url_for('static', filename=video_name)
    url_for('static', filename=comment_name)
    return render_template(
        'video.html',
        video_path=f'/static/{video_name}',
        comment_path=f'/static/{comment_name}',
        id=_id
    )


@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        milli_time_str = str(round(time.time() * 1000))
        video_name = f'upload_{milli_time_str}.mp4'
        comment_name = f'upload_{milli_time_str}.ass'

        f = request.files['video']
        f.save(f'static/{video_name}')
        f = request.files['comment']
        f.save(f'static/{comment_name}')
        return redirect(url_for('show_video', video_name=video_name, comment_name=comment_name))


@app.route('/init')
def init():
    _id = request.args['id']
    video_id = 0
    Config.src_filepath = os.getcwd() + f'/static/upload_{_id}'  # os.path.join(os.getcwd(), f'/static/upload_{_id}')
    # print(Config.src_filepath)

    Preparer.prepare()

    extractor = Extractor(Config.src_filepath, video_id)
    extractor.frames()
    extractor.comments()

    # preprocessor = Preprocessor()
    # preprocessor.txt_to_json()
    # preprocessor.add_context_in_json([22, 261, 1234, 1575])

    # candidate = Candidate()
    # candidate.get()

    return ('', 200)


@app.route('/comment')
def comment():
    _id = request.args['id']
    data = []
    with open(f'{os.getcwd()}/static/upload_{_id}.ass', 'r', encoding='utf8') as f:
        comment_id = 0
        for line in f.readlines():
            if not line.startswith('Dialogue'):
                continue
            comment = line[line.rfind('}') + 1:].strip()
            time = line[line.find(',') + 1:line.find('.')]
            time = sum(x * int(t) for x, t in zip([3600, 60, 1], time.split(":")))
            data.append({
                'id': comment_id,
                'time': time,
                'comment': comment
            })
            comment_id += 1
    return jsonify(data)


if __name__ == '__main__':
    app.run(debug=True)
