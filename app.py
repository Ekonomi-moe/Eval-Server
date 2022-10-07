__VERSION__ = "1.0.1"

from prompt_toolkit import print_formatted_text as print
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit import PromptSession

class dummy():
    def __init__(self):
        pass

class Storage():
    def __init__(self):
        import importlib
        import ddr
        self.exit = False
        self.__VERSION__ = __VERSION__

        self.modules = dummy()
        self.modules.Thread = importlib.import_module("threading").Thread
        self.modules.base64 = importlib.import_module("base64")
        self.modules.time = importlib.import_module("time")
        self.modules.PIL = importlib.import_module("PIL")
        self.modules.io = importlib.import_module("io")
        self.modules.ddr = ddr.DDRWEB(self)
        self.threads = {}
        pass

    def parse_image(self, image, imgid: str):
        if self.check_eval_end(imgid) != None:
            return
        thread = self.modules.Thread(target=self.modules.ddr.eval_image, args=(image, imgid,))
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



from flask import *
from hashlib import sha256
from flask_cors import CORS
import os
import requests
import io


storage = Storage()
app = Flask(__name__)
storage.secret_key = os.urandom(12)
app.secret_key = storage.secret_key
session = PromptSession()
session.auto_suggest = AutoSuggestFromHistory()

CORS(app)

ALLOWED_EXTENSIONS = ['png', 'jpg', 'jpeg', 'webp', 'gif']

@app.before_request
def before_request():
    if 'X-Forwarded-For' in request.headers: print(request.headers['X-Forwarded-For'])

@app.route('/api/')
def main():
    #return 404 not found
    return {"status": 404, "message": "Not found"}, 404

@app.route('/api/ddr', methods=['POST'])
def get_images():
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
    
    timg = storage.modules.PIL.Image.open(io.BytesIO(image_binary))
    timg.save(storage.modules.ddr.imagePath / (imgid + ".png"), "PNG")
    storage.parse_image(io.BytesIO(image_binary), imgid)
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
        rtndata.update({"image": storage.get_image(imgid)})
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
    return Response(img.read_bytes(), mimetype="image/png")

@app.route('/api/ddr_imglist', methods=['GET'])
def return_imglist():
    return {"status": 200, "message": "OK", "data": list(storage.modules.ddr.database.keys())}

@app.route('/api/ddr_imglist_html', methods=['GET'])
def return_imglist_html():
    html = ""
    for imgid in sorted(storage.modules.ddr.database.keys()):
        html += '<a href="/api/ddr_img?id=' + imgid + '" target="_blank">' + imgid + '</a><br>'
    return html

@app.route('/api/ddr_delete', methods=['GET'])
def delete_image():
    if ('key' not in request.args) or ('key' not in request.json):
        return {"status": 400, "message": "Key not found"}, 400
    if request.args['key'] != storage.modules.base64.b64encode(storage.secret_key).decode('utf-8'):
        return {"status": 401, "message": "Unauthorized"}, 401
    elif request.json['key'] != storage.modules.base64.b64encode(storage.secret_key).decode('utf-8'):
        return {"status": 401, "message": "Unauthorized"}, 401

    if ('id' not in request.args) or ('id' not in request.json):
        return {"status": 400, "message": "ID not found"}, 400
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
POST로 이미지를 받고, id를 반환
GET으로 id를 받고, 참/거짓 반환
>> 참일시 이미지와 태그를 반환

POST
{
    "status": 200,
    "message": "OK",
    "data": {
        "id": "SHA256"
    }
}

GET
{
    "status": 200,
    "message": "OK",
    "data": {
        "general": [["girl", 0.5], ["catear", 0.3]],
        "character": "kaffu_chino",
        "rating": "safe"
    }
}
"""

if __name__ == '__main__':
    app.debug = True
    print("Secret key:", storage.modules.base64.b64encode(storage.secret_key).decode('utf-8'))
    #app.run(host="127.0.0.1", threaded=True, port=8080, use_reloader=False)
    appthread = storage.modules.Thread(target=app.run, kwargs={'host': '127.0.0.1', 'port': 8080, 'threaded': True, 'use_reloader': False})
    appthread.daemon = True
    appthread.start()
    try:
        while True:
            command = session.prompt("> ")
            if command == "exit":
                storage.exit = True
                break
            elif command == "secret":
                print(storage.modules.base64.b64encode(storage.secret_key).decode('utf-8'))
            elif command == "":
                pass
            else:
                try:
                    print(eval(command))
                except KeyboardInterrupt:
                    storage.exit = True
                    break
                except Exception as e:
                    print("{error}: {message}".format(error=type(e).__name__, message=e))
    except KeyboardInterrupt:
        pass







    
