__VERSION__ = "1.1.1"

from prompt_toolkit import print_formatted_text, ANSI
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit import PromptSession
print = print_formatted_text

class dummy():
    def __init__(self):
        pass

class Storage():
    def __init__(self):
        import importlib
        import ddr
        self.exit = False
        self.__VERSION__ = __VERSION__
        self.config = None

        self.modules = dummy()
        self.modules.Thread = importlib.import_module("threading").Thread
        self.modules.base64 = importlib.import_module("base64")
        self.modules.time = importlib.import_module("time")
        self.modules.PIL = importlib.import_module("PIL")
        self.modules.io = importlib.import_module("io")
        self.modules.ddr = ddr.DDRWEB(self)
        self.threads = {}
        pass

    def parse_image(self, image, imgid: str, notsave: bool = False):
        if self.check_eval_end(imgid) != None:
            return
        thread = self.modules.Thread(target=self.modules.ddr.eval_image, args=(image, imgid, notsave))
        thread.start()
        self.threads.update({imgid: thread})
        pass

    def check_eval_end(self, imgid: str):
        if imgid in self.threads:
            return False
        elif imgid in self.modules.ddr.database:
            return True
        else:
            return None

    def get_eval_result(self, imgid: str):
        return self.modules.ddr.database[imgid]
    
    def get_image(self, imgid):
        img = self.modules.ddr.imagePath / (imgid + ".png")
        if img.exists(): 
            return self.modules.base64.b64encode(img.read_bytes()).decode("utf-8")
        else:
            return None
    
    def delete_image(self, imgid):
        img = self.modules.ddr.imagePath / (imgid + ".png")
        if img.exists(): 
            img.unlink()
            self.modules.ddr.database.pop(imgid)
            self.modules.ddr.onesave = True
            return True
        else:
            return False


from flask import Flask, request, send_file
from hashlib import sha256
from flask_cors import CORS
import logging
import os
import requests
import io

class PromptHandler(logging.StreamHandler):
    def emit(self, record):
        msg = self.format(record)
        print_formatted_text(ANSI(msg))

storage = Storage()
app = Flask(__name__)
app.secret_key = sha256(os.urandom(32)).hexdigest()[:6]
session = PromptSession()
session.auto_suggest = AutoSuggestFromHistory()
CORS(app)

logger = logging.getLogger("werkzeug")
logger.handlers = [PromptHandler()]

if storage.config.proxy:
    from werkzeug.middleware.proxy_fix import ProxyFix
    app.wsgi_app = ProxyFix(
        app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1
    )

ALLOWED_EXTENSIONS = ['png', 'jpg', 'jpeg', 'webp', 'gif']

@app.route('/api/')
def main():
    #return 404 not found
    return {"status": 404, "message": "Not found"}, 404

@app.route('/api/ddr', methods=['POST'])
def get_images():
    typ = ""
    notsave = False
    try:
        if ('file' in request.files): typ = "file"
    except:
        pass
    try:
        if 'file' in request.json: typ = "json"
    except:
        pass

    if typ == "":
        return {"status": 400, "message": "File not found"}, 400

    if typ == "file":
        image = request.files.get('file')
        if image.filename.split('.')[-1].lower() not in ALLOWED_EXTENSIONS:
            return {"status": 400, "message": "File extension not allowed"}, 400
        image_binary = image.read()
        imgid = sha256(image_binary).hexdigest()
    elif typ == "json":
        if request.json["file"]["type"] == "base64":
            image_binary = storage.modules.base64.b64decode(request.json["file"]["data"])
            imgid = sha256(image_binary).hexdigest()
        elif request.json["file"]["type"] == "url":
            rtn = requests.get(request.json["file"]["data"])
            if rtn.status_code != 200:
                return {"status": 400, "message": "File not found"}, 400
            image_binary = rtn.content
            imgid = sha256(image_binary).hexdigest()
        elif request.json["file"]["type"] == "binary":
            image_binary = request.json["file"]["data"]
            imgid = sha256(image_binary).hexdigest()
        if "notsave" in request.json:
            notsave = True
    
    if not notsave:
        timg = storage.modules.PIL.Image.open(io.BytesIO(image_binary))
        timg.save(storage.modules.ddr.imagePath / (imgid + ".png"), "PNG")
    storage.parse_image(io.BytesIO(image_binary), imgid, notsave)
    return {"status": 200, "message": "OK", "data": {"id": imgid}}, 200

@app.route('/api/ddr_bulk', methods=['POST'])
def get_bulk_images():
    typ = ""
    try:
        if ('file' in request.files): typ = "file"
    except:
        pass
    try:
        if 'file' in request.json: typ = "json"
    except:
        pass

    if typ == "":
        return {"status": 400, "message": "File not found"}, 400

    ok = 0
    failed = 0
    failed_list = []
    ok_list = []
    if typ == "file":
        for image in request.files.getlist('file'):
            if image.filename.split('.')[-1].lower() not in ALLOWED_EXTENSIONS:
                failed += 1
                failed_list.append({image.filename: "File extension not allowed"})
                continue
            image_binary = image.read()
            imgid = sha256(image_binary).hexdigest()
            try:
                timg = storage.modules.PIL.Image.open(io.BytesIO(image_binary))
                timg.save(storage.modules.ddr.imagePath / (imgid + ".png"), "PNG")
                storage.parse_image(io.BytesIO(image_binary), imgid)
                ok_list.append(imgid)
                ok += 1
            except Exception as e:
                failed += 1
                failed_list.append({imgid: str(e)})
                continue
    elif typ == "json":
        if request.json["file"]["type"] == "base64":
            for image_base64 in request.json["file"]["data"]:
                image_binary = storage.modules.base64.b64decode(image_base64)
                imgid = sha256(image_binary).hexdigest()
                try:
                    timg = storage.modules.PIL.Image.open(io.BytesIO(image_binary))
                    timg.save(storage.modules.ddr.imagePath / (imgid + ".png"), "PNG")
                    storage.parse_image(io.BytesIO(image_binary), imgid)
                    ok_list.append(imgid)
                    ok += 1
                except Exception as e:
                    failed += 1
                    failed_list.append({imgid: str(e)})
                    continue
        elif request.json["file"]["type"] == "url":
            for image_url in request.json["file"]["data"]:
                rtn = requests.get(image_url)
                if rtn.status_code != 200:
                    failed_list.append({imgid: str(rtn.status_code)+" "+rtn.text})
                    failed += 1
                    continue
                image_binary = rtn.content
                imgid = sha256(image_binary).hexdigest()
                try:
                    timg = storage.modules.PIL.Image.open(io.BytesIO(image_binary))
                    timg.save(storage.modules.ddr.imagePath / (imgid + ".png"), "PNG")
                    storage.parse_image(io.BytesIO(image_binary), imgid)
                    ok_list.append(imgid)
                    ok += 1
                except Exception as e:
                    failed += 1
                    failed_list.append({imgid: str(e)})
        elif request.json["file"]["type"] == "binary":
            image_binary = request.json["file"]["data"]
            imgid = sha256(image_binary).hexdigest()
            try:
                timg = storage.modules.PIL.Image.open(io.BytesIO(image_binary))
                timg.save(storage.modules.ddr.imagePath / (imgid + ".png"), "PNG")
                storage.parse_image(io.BytesIO(image_binary), imgid)
                ok_list.append(imgid)
                ok += 1
            except Exception as e:
                failed += 1
                failed_list.append({imgid: str(e)})

    if failed == 0:
        return {"status": 200, "message": "OK", "data": {"ok": ok, "ok_list": ok_list}}, 200
    else:
        return {"status": 500, "message": "Something Failed", "data": {"ok": ok, "ok_list": ok_list, "failed": failed, "failed_list": failed_list}}, 500

@app.route('/api/ddr', methods=['GET'])
def return_tags():
    try:
        if ('id' not in request.args) and ('id' not in request.json):
            return {"status": 400, "message": "ID not found"}, 400
        imgid = request.args['id']
    except:
        try:
            imgid = request.json['id']
        except:
            return {"status": 400, "message": "ID not found"}, 400
    
    eval_status = storage.check_eval_end(imgid)
    if eval_status is None:
        return {"status": 404, "message": "Id not found on work chain."}, 404
    elif eval_status is False:
        #202 Image is still processing
        return {"status": 202, "message": "Image is still processing"}, 202
    else:
        #return {"status": 202, "message": "Image is still processing"}, 202
        rtndata = {}
        
        rtndata.update(storage.get_eval_result(imgid))
        if storage.config.imgcdn == None: rtndata.update({"image": storage.get_image(imgid)})
        rtndata.update({"id": imgid})
        lists = []
        for i in storage.get_eval_result(imgid)["general"]:
            lists.append(i)
        rtndata.update({"general_list": lists})

        return {"status": 200, "message": "OK", "data": rtndata}, 200

    pass

@app.route('/api/ddr_img', methods=['GET'])
def return_image():
    try:
        if ('id' not in request.args) and ('id' not in request.json):
            return {"status": 400, "message": "ID not found"}, 400
        imgid = request.args['id']
    except:
        try:
            imgid = request.json['id']
        except:
            return {"status": 400, "message": "ID not found"}, 400
    
    if storage.check_eval_end(imgid) is None:
        return {"status": 500, "message": "Cannot find id in work and database."}, 500
    # return raw file
    img = storage.modules.ddr.imagePath / (imgid + ".png")
    if not img.exists(): return {"status": 404, "message": "Image not found"}, 404
    return send_file(img, mimetype='image/png')

@app.route('/api/ddr_imglist', methods=['GET'])
def return_imglist():
    return {"status": 200, "message": "OK", "data": list(storage.modules.ddr.database.keys())}

@app.route('/api/ddr_imglist_html', methods=['GET'])
def return_imglist_html():
    html = ""
    if storage.config.imgcdn != None:
        url = '<a href="//{cdnurl}/{imgid}.png" target="_blank">{imgid}</a><br>'.format(cdnurl=storage.config.imgcdn, imgid="{imgid}")
    else:
        url = '<a href="/api/ddr_img?id={imgid}" target="_blank">{imgid}</a><br>'
    for imgid in sorted(storage.modules.ddr.database.keys()):
        html += url.format(imgid=imgid)
    return html

@app.route('/api/ddr_delete', methods=['GET'])
def delete_image():
    try:
        key = request.args['key']
    except:
        try:
            key = request.json['key']
        except:
            return {"status": 400, "message": "Key not found"}, 400

    if key != app.secret_key:
        return {"status": 401, "message": "Unauthorized"}, 401

    try:
        imgid = request.args['id']
    except:
        try:
            imgid = request.json['id']
        except:
            return {"status": 400, "message": "ID not found"}, 400

    if storage.check_eval_end(imgid) is None:
        return {"status": 500, "message": "Cannot find id in work and database."}, 500

    storage.delete_image(imgid)
    return {"status": 200, "message": "OK"}, 200

"""
POST /api/ddr: Upload image, return id (sha256)
GET /api/ddr: Send id with args or json, if exist return tags
GET /api/ddr_img: Send id with args or json, if exist return image
GET /api/ddr_imglist: Return list of id
GET /api/ddr_imglist_html: Return list of id with html

POST /api/ddr
{
    "status": 200,
    "message": "OK",
    "data": {
        "id": "SHA256"
    }
}

GET /api/ddr
{
    "status": 200,
    "message": "OK",
    "data": {
        "id": "SHA256",
        "general": [["girl", 0.5], ["catear", 0.3]], // Multiple tags
        "character": [["rem_(re:zero)", 0.5], ["ram_(re:zero)", 0.4]], // Multiple tags, if null: []
        "rating": "safe", // One tag => safe, explicit, questionable
        "image": "BASE64DATA" # When imgcdn is False
    }
}
"""

if __name__ == '__main__':
    app.debug = True
    print("Secret key:", app.secret_key)
    appthread = storage.modules.Thread(target=app.run, kwargs={'host': '127.0.0.1', 'port': storage.modules.ddr.config.port, 'threaded': True, 'use_reloader': False})
    appthread.daemon = True
    appthread.start()
    try:
        while True:
            command = session.prompt("> ")
            if command == "exit":
                storage.exit = True
                break
            elif command == "secret":
                print(app.secret_key)
            elif command.startswith("delete "):
                rtn = storage.delete_image(command[7:])
                if rtn is True:
                    print("Deleted")
                else:
                    print("Error")
            elif command == "":
                pass
            else:
                try:
                    exec(command)
                except KeyboardInterrupt:
                    storage.exit = True
                    break
                except Exception as e:
                    print("{error}: {message}".format(error=type(e).__name__, message=e))
    except KeyboardInterrupt:
        pass
