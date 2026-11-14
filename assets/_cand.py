import os, urllib.request
out = r"C:\Users\admin\Desktop\冷咖啡全自动破甲\assets\cand"
os.makedirs(out, exist_ok=True)
ids = [
 "photo-1507525428034-b723cf961d3e",
 "photo-1505118380757-91f5f5632de0",
 "photo-1439405326854-014607f694d7",
 "photo-1471922694854-ff1b63b20054",
 "photo-1518837695005-2083093ee35b",
 "photo-1454372182658-c712e4c5a1db",
 "photo-1468413253725-0d5181091126",
 "photo-1498623116890-37e912163d5d",
]
for i, pid in enumerate(ids):
    url = "https://images.unsplash.com/%s?w=640&q=80&fm=jpg" % pid
    try:
        req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0"})
        data = urllib.request.urlopen(req, timeout=30).read()
        p = os.path.join(out, "%02d.jpg" % i)
        open(p, "wb").write(data)
        print(i, pid, len(data))
    except Exception as e:
        print(i, pid, "ERR", e)