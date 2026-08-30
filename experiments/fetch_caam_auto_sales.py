"""Discover and extract CAAM monthly automobile sales releases."""
from __future__ import annotations
import argparse,hashlib,json,re
from pathlib import Path
from urllib.parse import urljoin
import pandas as pd,requests
from bs4 import BeautifulSoup
BASE="http://www.caam.org.cn/chn/4/cate_31/"
SUPPLEMENTAL={"202202":("2022年2月汽车工业经济运行情况",f"{BASE}con_5235503.html")}
def number(value):return float(value.replace(",",""))
def signed(word,value):return number(value)*(1 if word=="增长" else -1)
def extract(text):
 text=re.sub(r"\s+","",text)
 m=re.search(r"(?<![0-9-])(?:20\d{2}年\d{1,2}月|当月|\d{1,2}月)[，,]?汽车产销(?:分别)?(?:完成|达到|为)?([\d.,]+)万辆和([\d.,]+)万辆.*?同比(?:分别)?(增长|下降)([\d.]+)%和(增长|下降)?([\d.]+)%",text)
 if m:
  direction2=m.group(5) or m.group(3);return {"production_10k":number(m.group(1)),"sales_10k":number(m.group(2)),"production_yoy":signed(m.group(3),m.group(4)),"sales_yoy":signed(direction2,m.group(6))}
 m=re.search(r"(?<![0-9-])(?:20\d{2}年\d{1,2}月|当月|\d{1,2}月)[，,]?汽车生产([\d.,]+)万辆.*?同比(增长|下降)([\d.]+)%[；;].*?销售([\d.,]+)万辆.*?同比(增长|下降)([\d.]+)%",text)
 if m:return {"production_10k":number(m.group(1)),"sales_10k":number(m.group(4)),"production_yoy":signed(m.group(2),m.group(3)),"sales_yoy":signed(m.group(5),m.group(6))}
 return None
def run(start_year,end_year,out_dir,out_csv,manifest_path):
 out=Path(out_dir);out.mkdir(parents=True,exist_ok=True);links={}
 for page in range(1,61):
  url=f"{BASE}list_{page}.html";html=requests.get(url,headers={"User-Agent":"Mozilla/5.0"},timeout=30).content;soup=BeautifulSoup(html,"html.parser")
  for a in soup.find_all("a",href=True):
   title=a.get_text(" ",strip=True);m=re.search(r"(20\d{2})年(\d{1,2})月汽车工业(?:产销|经济运行).*?(?:简析|综述)",title)
   if m and start_year<=int(m.group(1))<=end_year:links.setdefault(f"{m.group(1)}{int(m.group(2)):02d}",(title,urljoin(url,a["href"])))
 links.update({month:item for month,item in SUPPLEMENTAL.items() if start_year<=int(month[:4])<=end_year})
 records=[]
 ocr=None
 for month,(title,url) in sorted(links.items()):
  content=requests.get(url,headers={"User-Agent":"Mozilla/5.0"},timeout=30).content;path=out/f"{month}.html";path.write_bytes(content);soup=BeautifulSoup(content,"html.parser");text=soup.get_text(" ",strip=True);release=re.search(r"发布时间[:：]?\s*(\d{4})[-.年](\d{1,2})[-.月](\d{1,2})",text);values=extract(text);method="HTML"
  if not values:
   images=[urljoin(url,i.get("src")) for i in soup.select(".form-fourBox img[src]")]
   if images:
    if ocr is None:
     from rapidocr_onnxruntime import RapidOCR
     ocr=RapidOCR()
    blocks=[]
    for index,image_url in enumerate(images):
     response=requests.get(image_url,headers={"User-Agent":"Mozilla/5.0"},timeout=60)
     if response.status_code!=200:continue
     image_path=out/f"{month}-{index}.img";image_path.write_bytes(response.content)
     try:result,_=ocr(str(image_path))
     except Exception:continue
     blocks.extend(x[1] for x in result or [])
    ocr_text="\n".join(blocks);(out/f"{month}.ocr.txt").write_text(ocr_text);values=extract(ocr_text);method="OCR"
  records.append({"month":month,"title":title,"url":url,"release_date":f"{release.group(1)}-{int(release.group(2)):02d}-{int(release.group(3)):02d}" if release else None,"status":"OK" if values else "UNEXTRACTED","extraction_method":method,"sha256":hashlib.sha256(content).hexdigest(),**(values or {})})
 frame=pd.DataFrame(records);frame.to_csv(out_csv,index=False);manifest={"source":"CAAM","start_year":start_year,"end_year":end_year,"discovered":len(frame),"extracted":int(frame.status.eq("OK").sum()) if len(frame) else 0,"missing_months":[f"{y}{m:02d}" for y in range(start_year,end_year+1) for m in range(1,13) if f"{y}{m:02d}" not in set(frame.month.astype(str))],"unextracted":frame.loc[frame.status.ne("OK"),["month","url"]].to_dict("records") if len(frame) else [],"output":out_csv};Path(manifest_path).write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n");return manifest
def main(argv=None):
 p=argparse.ArgumentParser();p.add_argument("--start-year",type=int,default=2018);p.add_argument("--end-year",type=int,default=2025);p.add_argument("--out-dir",default="overall/a-share-auto-sales-raw");p.add_argument("--out-csv",default="overall/a-share-auto-sales-monthly.csv");p.add_argument("--manifest",default="overall/a-share-auto-sales-manifest.json");a=p.parse_args(argv);print(json.dumps(run(a.start_year,a.end_year,a.out_dir,a.out_csv,a.manifest),ensure_ascii=False,indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
