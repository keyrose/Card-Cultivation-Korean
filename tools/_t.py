import UnityPy,sys
from PIL import Image,ImageDraw
from common import *
rel,out=sys.argv[1],sys.argv[2]
d,_=read_dat(original("StreamingAssets/"+rel)); env=UnityPy.load(d)
ims=sorted([(o.peek_name(),o) for o in env.objects if o.type.name=="Texture2D"],key=lambda x:x[0])
T=150; cols=10
part=ims[:100]; rows=(len(part)+cols-1)//cols
sh=Image.new("RGB",(cols*T,rows*(T+12)),(90,90,90)); dr=ImageDraw.Draw(sh)
for i,(n,o) in enumerate(part):
    im=o.read().image.convert("RGBA"); im.thumbnail((T-4,T-4)); x,y=(i%cols)*T,(i//cols)*(T+12)
    sh.paste(im,(x+2,y+2),im); dr.rectangle([x,y,x+T-1,y+T+11],outline=(0,0,0)); dr.text((x+2,y+T),f"{i}:{n}"[:22],fill=(255,255,0))
sh.save(out); print(len(ims))
