import json
import os
import threading
import time
from typing import List

from AutoDanmuGen.config import Config
from AutoDanmuGen.core.extract import Extractor
from AutoDanmuGen.core.preprocess import Preprocessor
from AutoDanmuGen.core.candicate import Candidate
from AutoDanmuGen.core.danmu import Danmu
from flask import (
    Flask,
    jsonify,
    redirect,
    render_template,
    request,
    url_for
)


app = Flask(__name__)


HTTP_OK = 200
HTTP_BAD_REQUEST = 400
HTTP_INTERNAL_SERVER_ERROR = 500


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/preview')
def preview():
    _id = request.args.get('id')
    if _id is None:
        return ("", HTTP_BAD_REQUEST)

    url_for('static', filename='{_id}/upload.mp4')
    url_for('static', filename='{_id}/upload.ass')

    return render_template('preview.html', id=_id)


@app.route('/result')
def result():
    _id = request.args.get('id')
    if _id is None:
        return ("", HTTP_BAD_REQUEST)

    _comment_idx = request.args.get('comment_idx')
    if _comment_idx is None:
        return ("", HTTP_BAD_REQUEST)

    return render_template('result.html', id=_id, comment_idx=_comment_idx)


@app.route('/comments')
def comments():
    _id = request.args['id']
    if _id is None:
        return ("", HTTP_BAD_REQUEST)

    extractor = Extractor(f'{os.getcwd()}/static/{_id}/upload')
    extractor.comment_txt = f'{os.getcwd()}/static/{_id}/comment.txt'
    extractor.comments()

    data = []
    with open(f'{os.getcwd()}/static/{_id}/comment.txt', 'r', encoding='utf8') as f:
        comment_id = 0
        for line in f.readlines():
            cols = line.strip().split('\t')
            data.append({
                'id': comment_id,
                'time': cols[1],
                'comment': cols[2]
            })
            comment_id += 1
    return jsonify(data)


@app.route('/poll')
def poll():
    _id = request.args['id']
    if _id is None:
        return ("", HTTP_BAD_REQUEST)

    path = f'{os.getcwd()}/static/{_id}/'
    if os.path.isfile(os.path.join(path, 'test-result.json')):
        return "done"
    if os.path.isfile(os.path.join(path, 'comment-candidate.json')):
        return "Testing / Predicting"
    if os.path.isfile(os.path.join(path, 'comment-context.json')):
        return "Adding Candidates into -context.json"
    if os.path.isfile(os.path.join(path, 'comment.json')):
        return "Adding Contexts into .json"
    if os.path.isfile(os.path.join(path, 'frames')):
        return "Converting .txt to .json"
    if os.path.exists(os.path.join(path, 'comment.txt')):
        return "Extracting Video Frames"
    return "failed"


@app.route('/test')
def get_test():
    _id = request.args.get('id')
    if _id is None:
        return ("", HTTP_BAD_REQUEST)

    data = []

    # id, time, comments, surrounding_comments
    with open(f'{os.getcwd()}/static/{_id}/comment-context.json', 'r', encoding='utf8') as f:
        json_datas = []
        for line in f:
            tmp = json.loads(line)
            json_datas.append(tmp)
        for i in json_datas:
            comment = i['comment'][len(i['comment']) // 2]
            comment = comment.replace(' ', '')

            surrounding_comments = i['context']
            surrounding_comments = surrounding_comments.split('<&&&>')
            surrounding_comments = [x.replace(' ', '') for x in surrounding_comments]

            data.append({
                'id': i['id'],
                'time': i['time'],
                'comments': comment,
                'surrounding_comments': surrounding_comments,
                'result': []
            })

    # result
    with open(f'{os.getcwd()}/static/{_id}/test-result.json', 'r', encoding='utf8') as f:
        json_datas = json.loads(f.read())

        for (j, d) in zip(json_datas, data):
            d['result'] = j

    return jsonify(data)


@app.route('/upload', methods=['POST'])
def upload():
    _id = str(round(time.time() * 1000))

    if not os.path.exists(f'static/{_id}/'):
        os.mkdir(f'static/{_id}/')

    f = request.files['video']
    if f is None:
        return ("", HTTP_BAD_REQUEST)
    f.save(f'static/{_id}/upload.mp4')

    f = request.files['comment']
    if f is None:
        return ("", HTTP_BAD_REQUEST)
    f.save(f'static/{_id}/upload.ass')

    return redirect(url_for('preview', id=_id))


@app.route('/test', methods=['POST'])
def post_test():
    _id = request.args.get('id')
    if _id is None:
        return ("", HTTP_BAD_REQUEST)

    checked_comment_id = request.form.getlist('comments')
    if checked_comment_id is None or len(checked_comment_id) <= 0:
        return ("", HTTP_BAD_REQUEST)
    checked_comment_id = [int(x) for x in checked_comment_id]

    thread = threading.Thread(
        target=submethod_for_test,
        args=[_id, checked_comment_id]
    )
    thread.daemon = True
    thread.start()

    return redirect(url_for('result', id=_id))


@app.route('/predict', methods=['POST'])
def predict():
    pass


def submethod_for_test(_id: str, checked_comment_id: List[int]):
    # Extract frames from video
    if not os.path.exists(f'{os.getcwd()}/static/{_id}/frames'):
        extractor = Extractor(f'{os.getcwd()}/static/{_id}/upload')
        if not os.path.exists(f'{os.getcwd()}/static/{_id}/frames'):
            os.mkdir(f'{os.getcwd()}/static/{_id}/frames')
        extractor.frames_outdir = f'{os.getcwd()}/static/{_id}/frames'
        extractor.frames()

    Config.comment_txt = f'{os.getcwd()}/static/{_id}/comment.txt'
    Config.comment_json = f'{os.getcwd()}/static/{_id}/comment.json'
    Config.comment_context_json = f'{os.getcwd()}/static/{_id}/comment-context.json'
    preprocessor = Preprocessor()

    # Convert .txt to .json
    preprocessor.txt_to_json()

    # Add context to into the .json file
    preprocessor.add_context_in_json(checked_comment_id)

    # Add candidates to the -context.json file
    Config.comment_candidate_json = f'{os.getcwd()}/static/{_id}/comment-candidate.json'
    candidate = Candidate()
    candidate.get()

    # Start Danmu test
    danmu = Danmu()
    test_result = danmu.test()
    with open(f'{os.getcwd()}/static/{_id}/test-result.json', 'w', encoding='utf8') as f:
        json_str_test_result = json.dumps(test_result)
        f.write(json_str_test_result)


if __name__ == '__main__':
    app.run(debug=True, threaded=True, port=5000)
