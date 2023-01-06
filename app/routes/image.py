from flask import  make_response
from flask_restx import Resource, Namespace
import os
from app.config import Config
from app.utils import get_logger
from werkzeug.utils import secure_filename

ns = Namespace('image', description="截图信息")

logger = get_logger()

def allowed_file(filename):
    ALLOWED_EXTENSIONS = ['jpg','png']
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

@ns.route('/<string:task_id>/<string:file_name>')
class ARLImage(Resource):

    def get(self, task_id, file_name):
        task_id = secure_filename(task_id)
        file_name = secure_filename(file_name)
        if not allowed_file(file_name):
            return
        imgpath = os.path.join(Config.SCREENSHOT_DIR,
                               '{task_id}/{file_name}'.format(task_id=task_id,
                                                              file_name=file_name))
        if os.path.exists(imgpath):
            image_data = open(imgpath, "rb").read()
            response = make_response(image_data)
            response.headers['Content-Type'] = 'image/jpg'
            return response
        else:
            image_data = open(Config.SCREENSHOT_FAIL_IMG, "rb").read()
            response = make_response(image_data)
            response.headers['Content-Type'] = 'image/jpg'
            return response







