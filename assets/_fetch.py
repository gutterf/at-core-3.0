import json, urllib.request, urllib.parse, os
out = r"C:\Users\admin\Desktop\冷咖啡全自动破甲\assets"
def get(url, path):
    req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0 LCS-UI/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = r.read()
    open(path, "wb").write(data)
    return len(data)
print("earth", get("https://upload.wikimedia.org/wikipedia/commons/9/97/The_Earth_seen_from_Apollo_17.jpg", os.path.join(out,"earth_apollo17.jpg")))
params = {
  "action":"query","format":"json","generator":"search",
  "gsrsearch":"seascape dusk horizon ocean","gsrnamespace":"6","gsrlimit":"20",
  "prop":"imageinfo","iiprop":"url|size|mime","iiurlwidth":"900"
}
url = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(params)
req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0 LCS-UI/1.0"})
data = json.load(urllib.request.urlopen(req, timeout=60))
pages = data.get("query",{}).get("pages",{})
for p in pages.values():
    ii = p.get("imageinfo",[{}])[0]
    print(p.get("title"), "|", ii.get("width"), "x", ii.get("height"), "|", ii.get("thumburl"))