from prompt_toolkit import print_formatted_text as print

class dummy():
    def __init__(self):
        pass

class DDRWEB(Exception):
    def __init__(self, storage):
        self.storage = storage
        self.ekonomi = {"general": [["ekonomi",1],["mascot",1],["solo",1],["no_background",1],["smile",1],["helloyunho",1],["Roul_",1],["this_is_just_a_joke",1]],"character": ["ekonomi", 1],"rating": "safe"}

        import importlib

        self.importlib = importlib
        try:
            self.modules = storage.modules
        except:
            self.modules = dummy()

        self.modules.Thread = importlib.import_module("threading").Thread
        self.modules.sha256 = importlib.import_module("hashlib").sha256
        self.modules.dd = importlib.import_module("deepdanbooru")
        self.modules.tf = importlib.import_module("tensorflow")
        self.modules.json = importlib.import_module("json")
        self.modules.time = importlib.import_module("time")
        self.modules.gc = importlib.import_module("gc")
        self.Path = importlib.import_module("pathlib").Path
        self.onesave = False

        self.config = dummy()
        self.data = dummy()
        self.update = False

        self.load_config()
        self.storage.config = self.config
        self.load_data()
        self.load_database()


        self.dbqueue = []
        self.dbadmin = self.modules.Thread(target=self.dba)
        self.dbadmin.daemon = True
        self.dbadmin.start()

        UpdateStatus = self.DBUpdateCheck()
        if UpdateStatus:
            self.update = False
        else:
            del(self.database["AIVersion"])
            del(self.database["APPVersion"])
        pass

    def DBUpdate(self, AIUpdate, APPUpdate):
        self.update = True
        if APPUpdate: 
            if "APPVersion" in self.database: APPVersionBefore = self.database["APPVersion"]
            else: APPVersionBefore = "First"
            print("Updating database APPVersion {befver} --> {ver}...".format(befver=APPVersionBefore, ver=self.storage.__VERSION__))
        if AIUpdate: 
            if "AIVersion" in self.database: AIVersionBefore = self.database["AIVersion"]
            else: AIVersionBefore = "First"
            print("Updating database AIVersion {befver} --> {ver}...".format(befver=AIVersionBefore, ver=self.config.AIVersion))


        dataPath = self.workPath / "database.json"
        try:
            if AIUpdate and APPUpdate:
                dataPath.rename(dataPath.parent / "database_bef_app_{appver}_ai_{aiver}.json".format(appver=APPVersionBefore, aiver=AIVersionBefore))
            elif AIUpdate:
                dataPath.rename(dataPath.parent / "database_bef_ai_{aiver}.json".format(aiver=AIVersionBefore))
            elif APPUpdate:
                dataPath.rename(dataPath.parent / "database_bef_app_{appver}.json".format(appver=APPVersionBefore))
        except FileExistsError:
            pass
        self.database = {}
        self.database.update({"ekonomi": self.ekonomi})
        images = list(self.imagePath.iterdir())

        self.work_queue_update = {}

        for image in images:
            if image.suffix == ".png":
                if image.stem == "ekonomi": continue
                print("[{now}/{all}] {img}".format(now=images.index(image)+1, all=len(images), img=image.stem))
                #self.eval_image(self.modules.io.BytesIO(image.read_bytes()), image.stem)
                while True:
                    if len(self.work_queue_update) < 10:
                        ithr = self.modules.Thread(target=self.eval_image_update, args=(self.modules.io.BytesIO(image.read_bytes()), image.stem))
                        ithr.daemon = True
                        ithr.start()
                        self.work_queue_update.update({image.stem: ithr})
                        break
                    else:
                        self.modules.time.sleep(1)
        while True:
            if len(self.work_queue_update) == 0: break
            self.modules.time.sleep(1)

        print("Database update done.")
        if AIUpdate: print("AI Version: {ver}".format(ver=self.config.AIVersion))
        if APPUpdate: print("APP Version: {ver}".format(ver=self.storage.__VERSION__))
        while len(self.dbqueue) != 0: self.modules.time.sleep(0.5)
        self.update = False
        pass

    def eval_image_update(self, image, image_name):
        try:
            self.eval_image(image, image_name)
        except Exception as e:
            print("ERROR: {e}".format(e=e))
        del(self.work_queue_update[image_name])
        pass

    def DBUpdateCheck(self):
        AIVersion = False
        APPVersion = False
        if "AIVersion" not in self.database: AIVersion = True
        elif self.database["AIVersion"] != self.config.AIVersion: AIVersion = True
        if "APPVersion" not in self.database: APPVersion = True
        elif self.database["APPVersion"] != self.storage.__VERSION__:
            APPVersionBefore = self.database["APPVersion"].split(".")
            APPVersionAfter = self.storage.__VERSION__.split(".")
            if APPVersionBefore[0] != APPVersionAfter[0] or APPVersionBefore[1] != APPVersionAfter[1]: APPVersion = True
            elif "pre" in APPVersionAfter[2]: APPVersion = True
        
        if AIVersion or APPVersion: 
            self.DBUpdate(AIVersion, APPVersion)
            return True
        else: return False

    def dba(self):
        work = False
        while True:
            if (self.storage.exit) and (work == False) and (len(self.dbqueue) == 0): break
            
            if len(self.dbqueue) != 0:
                work = True
                queue = self.dbqueue.pop(0)
                if list(queue.keys())[0] in self.database:
                    raise KeyError("Image already exists in database")
                self.database.update(queue)
                if self.update == False:
                    self.storage.threads.pop(list(queue.keys())[0])
            
            if (work and (len(self.dbqueue) == 0) and self.update == False) or self.onesave:
                if self.onesave: self.onesave = False
                if (work and (len(self.dbqueue) == 0) and self.update == False): work = False

                database = dict(self.database)

                database.update({"AIVersion": self.config.AIVersion})
                database.update({"APPVersion": self.storage.__VERSION__})

                dataPath = self.workPath / "database.json"
                f = open(dataPath, "w", encoding="utf-8")
                self.modules.json.dump(database, f, ensure_ascii=False) #indent=4
                f.close()
                del(database)
                self.modules.gc.collect()

            
            if work == False: self.modules.time.sleep(1)

    def load_config(self):
        configPath = self.Path(".") / "config.json"
        if not configPath.exists():
            raise FileNotFoundError("Config file not found. Please move a config_example file.")
        f = open("config.json", "r", encoding="utf-8")
        config = self.modules.json.load(f)
        f.close()
        
        self.config.model_path = self.Path(config["model_path"])
        self.config.tag_path = self.Path(config["tag_path"])
        self.config.tag_general_path = self.Path(config["tag_general_path"])
        self.config.tag_character_path = self.Path(config["tag_character_path"])
        self.config.work_path = self.Path(config["work_path"])
        self.config.threshold = config["threshold"]
        self.config.AIVersion = config["AIVersion"]
        self.config.proxy = config["proxy"]
        self.config.port = config["port"]
        if config["imgcdn"]:
            self.config.imgcdn = self.Path(config["imgcdn_url"])
        else:
            self.config.imgcdn = None

        self.check_config()
    
    def check_config(self):
        self.config.modelPath = self.Path(self.config.model_path)
        if self.config.model_path.exists() == False: raise FileNotFoundError("Model not found")
        self.config.tagPath = self.Path(self.config.tag_path)
        if self.config.tagPath.exists() == False: raise FileNotFoundError("Tag file not found")
        self.config.tagGeneralPath = self.Path(self.config.tag_general_path)
        if self.config.tagGeneralPath.exists() == False: raise FileNotFoundError("Tag general file not found")
        self.config.tagCharacterPath = self.Path(self.config.tag_character_path)
        if self.config.tagCharacterPath.exists() == False: raise FileNotFoundError("Tag character file not found")

        self.workPath = self.Path(self.config.work_path)
        self.workPath.mkdir(parents=True, exist_ok=True)

        self.imagePath = self.workPath / "images"
        self.imagePath.mkdir(exist_ok=True)

        if self.config.threshold < 0 or self.config.threshold > 1: raise ValueError("threshold must be between 0 and 1")
        pass

    def load_database(self):
        dataPath = self.workPath / "database.json"
        if dataPath.exists():
            f = open(dataPath, "r", encoding="utf-8")
            self.database = self.modules.json.load(f)
            f.close()
        else:
            self.database = {}
            self.database.update({"AIVersion": self.config.AIVersion})
            self.database.update({"APPVersion": self.storage.__VERSION__})
            self.database.update({"ekonomi": self.ekonomi})
            f = open(dataPath, "w", encoding="utf-8")
            self.modules.json.dump(self.database, f, ensure_ascii=False)
            f.close()

        pass

    def save_imgdata(self, image_name, sort_general, character, rating):
        self.dbqueue.append({image_name: {"general": sort_general, "character": character, "rating": rating}})
        self.save_database()
        pass

    def load_data(self):
        # model
        self.data.model = self.modules.tf.keras.models.load_model(self.config.modelPath, compile=False)

        # tags
        self.data.tags = dummy()
        with open(self.config.tagPath, "r", encoding="utf-8") as tags_stream:
            self.data.tags.all = [tag for tag in (tag.strip() for tag in tags_stream) if tag]
        with open(self.config.tagGeneralPath, "r", encoding="utf-8") as tags_stream:
            self.data.tags.general = [tag for tag in (tag.strip() for tag in tags_stream) if tag]
        with open(self.config.tagCharacterPath, "r", encoding="utf-8") as tags_stream:
            self.data.tags.character = [tag for tag in (tag.strip() for tag in tags_stream) if tag]

    def eval_image(self, image, imgid: str, notsave: bool = False):
        #image_name = imgid + ".png"
        #img_path = self.imagePath / image_name
        width = self.data.model.input_shape[2]
        height = self.data.model.input_shape[1]
        
        image = self.modules.dd.data.load_image_for_evaluate(image, width=width, height=height)
        image_shape = image.shape
        image = image.reshape((1, image_shape[0], image_shape[1], image_shape[2]))
        y = self.data.model.predict(image)[0]

        if notsave:
            self.storage.threads.pop(imgid)
            return

        result_dict = {}

        for i, tag in enumerate(self.data.tags.all):
            result_dict[tag] = y[i]

        sort_general = {}
        sort_rating = {}
        sort_character = {}

        # update with list
        for tag in self.data.tags.all:
            if "rating:" in tag:
                sort_rating.update({tag: result_dict[tag]})
            elif tag in self.data.tags.character and result_dict[tag] > self.config.threshold:
                sort_character.update({tag: result_dict[tag]})
            elif result_dict[tag] >= self.config.threshold:
                sort_general.update({tag: result_dict[tag]})
        
        sort_general_list = sorted(sort_general.items(), key=lambda x: x[1], reverse=True)
        sort_character_list = sorted(sort_character.items(), key=lambda x: x[1], reverse=True)
        sort_rating = sorted(sort_rating.items(), key=lambda x: x[1], reverse=True)
        #[('rating:safe', 1.5022916e-08), ('rating:explicit', 1.4161448e-08), ('rating:questionable', 1.4002417e-08)]

        sort_general = []
        sort_character = []
        for tag_gen, rate in sort_general_list: sort_general.append([str(tag_gen), float(rate)])
        for tag_char, rate in sort_character_list: sort_character.append([str(tag_char), float(rate)])

        self.dbqueue.append({imgid: {"general": sort_general, "character": sort_character, "rating": sort_rating[0][0].replace("rating:", "")}})
        
        return