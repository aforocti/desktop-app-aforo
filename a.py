import re

archivo = open("report.txt","r")
patter = r"\s+"
for line in archivo:
    spt = line.split(",")[2:]
    print(re.split(patter,spt[0]))
