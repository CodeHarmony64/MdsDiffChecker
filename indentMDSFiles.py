import os,os.path,sys,fnmatch,copy,traceback
from xml.dom.minidom import *

def cleanDOM(root):
    if root:
        nodeList = root.childNodes
        temp_list = copy.copy(nodeList)
        for node in temp_list:
            if node.nodeType  == Node.TEXT_NODE and node.nodeValue.isspace():
                nodeList.remove(node)
        for node in nodeList:
            cleanDOM(node)
    return


def indent(mds_path):
    file_list = []
    if not os.access(mds_path,os.W_OK):
        print 'Source MDS Path doesn\'t exist or No Write Access: '+mds_path
        return
    for dirpath,dirname,filenames in os.walk(mds_path):
        for filename in fnmatch.filter(filenames,'*.jsff'):
            file_list.append(os.path.join(dirpath,filename))
    for file in file_list:
        try:
            print "Currently Processing : "+file
            dom = parse(file)
            root = dom.documentElement
            cleanDOM(root)
            fp = open(file,'w+')
            fp.write(root.ownerDocument.toprettyxml(encoding="UTF-8"))
            fp.close()
        except Exception:
            print '######################  Failed for : '+file+'  ############################'
            print traceback.print_exc()
            print '###########################################################################'
    return

n = sys.argv.__len__()
for i in range(1,n):
    indent(sys.argv[i])

