import json, os, tempfile

def load_json(path):
    with open(path,'r',encoding='utf-8') as f:
        return json.load(f)

def save_json(path,data):
    directory=os.path.dirname(path) or "."
    fd,tmp=tempfile.mkstemp(suffix=".tmp",dir=directory)
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as f:
            json.dump(data,f,ensure_ascii=False,indent=2)
        os.replace(tmp,path)
    except Exception:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise