import xslt
import sys

if len(sys.argv) < 3:
	print "Usage: xsltproc.py <stylesheet> <document>"
	
proc = xslt.XSLTProcessor()
proc.setStylesheet(sys.argv[1])
msgs = []
s = proc.transform(sys.argv[2], messages=msgs)

for i in msgs:
	print "[MSG]: %s" % i
	
print s