import sys,copy,os,os.path,traceback,fnmatch,string
from xml.dom.minidom import *

source_mds_path = ''                        #script parameter to store path of the old/source mds
dest_mds_path = ''                          #script parameter to store path of the new/destination mds
relative_recur_path = ''                    #script parameter to store path of the directory which needs to be search recursively to look for respective source and destinaiton files relative to mds location
script_gen_path = ''                        #script parameter to store path where the new scripts will be generated
debug_flag = 0                              #script parameter to store debug flag can be 0 for Logs, 1 for Fine, 2 for finer, 3 for finest


source_files = []                           #Global able to store the list of all the source files that needs to be checked along absolute path
dest_files = []                             #Global able to store the list of all the destination files that needs to be compared along with absolute path


#Below mentioned global ables Require reset after each modifiedDFS iteration
curr_source_file = ''                       #Global able : Holds the source file currently being processed.
curr_dest_file = ''                         #Global able : Holds the destination file currenlty being processed.
warnings = []                               #Global List : Holds all the warnings for files currently being processed
id_set = set()                              #Global Set : Holds all the component and their children's ids which are already been inserted
manipulate_node = None                      #Global Node : Holds the reference to the maniuplate node of current UpgradeMeta, all the generated script nodes are appended to it
component_lib_file_root = None              #Global able to hold the refrence to root node of component Lib. All upgradeMeta nodes will be appended to this

class DebugFlag:
    LOG = 0
    FINE = 1
    FINER = 2
    FINEST = 3

def relativePath(path,relativ_to): #try catch block can be added to handle to see this doesn't return malformed path
    return path.replace(relativ_to,'',1)

def appendList(st,lst):#Adds all the items of the list to an existing set
    for itm in lst:
        st.add(itm)
    return

def printNodeList(message,node_list):# prints message + all the nodes in nodeList
    for node in node_list:
        print message + printNode(node)

def printNode(node,print_parent=1):
    comment = ''
    if not node:
        return 'None'
    elif node.nodeType != Node.ELEMENT_NODE:
        comment = 'Node :Text Node'
    elif node.hasAttribute('id'):
        comment = node.nodeName+' id:'+node.getAttribute('id')
    elif node.nodeName == 'f:facet':
        comment = node.nodeName+' name:'+node.getAttribute('name')
    elif node.nodeName == 'c:set':
        comment = node.nodeName+' var:'+node.getAttribute('var')+' value:'+node.getAttribute('value')
    elif node.nodeName == 'af:setActionListener':
        comment = node.nodeName+' from:'+node.getAttribute('from')+' to:'+node.getAttribute('to')
    else:
        comment = node.nodeName

    if(print_parent and node.parentNode.nodeType == Node.ELEMENT_NODE):
        comment = comment+' Parent: '+printNode(node.parentNode,0)

    return comment


def cleanDOM(root):
    if root:
        nodeList = root.childNodes
        temp_list = copy.copy(nodeList)
        for node in temp_list:
            if node.nodeType  == Node.TEXT_NODE or node.nodeType == Node.COMMENT_NODE or node.nodeType == Node.CDATA_SECTION_NODE:
                nodeList.remove(node)
        for node in nodeList:
            cleanDOM(node)
    return

def prepareFileList():
    global source_mds_path,dest_mds_path,relative_recur_path,source_files,dest_files
    source_path = os.path.join(source_mds_path, relative_recur_path)
    dest_path = os.path.join(dest_mds_path, relative_recur_path)
    if debug_flag >= DebugFlag.FINER: print 'Looking for source files in : ',source_path, '\nLooking for Destination files in : ',dest_path
    if not (os.access(os.path.join(source_mds_path, relative_recur_path), os.R_OK) and os.access(os.path.join(dest_mds_path, relative_recur_path), os.R_OK)):
        print('Wrong path given or path not accessible.')
        exitScript(6)

    for dirpath,dirnames,filenames in os.walk(os.path.join(source_mds_path, relative_recur_path)):
        for filename in fnmatch.filter(filenames,'*.jsff'):
            source_files.append(os.path.join(dirpath, filename))
    for dirpath,dirnames,filenames in os.walk(os.path.join(dest_mds_path, relative_recur_path)):
        for filename in fnmatch.filter(filenames,'*.jsff'):
            dest_files.append(os.path.join(dirpath, filename))

    source_files.sort()
    dest_files.sort()
    source_set = set()
    dest_set = set()
    print('***********Source Files to be processed*********')
    for source_file in source_files:
        print(source_file +'\t\t' +'relative path:\t' + relativePath(source_file, source_mds_path))
        source_set.add(os.path.basename(source_file))
    print('\n**********Destination Files to be processed***********')
    for dest_file in dest_files:
        print(dest_file +'\t\t' +'relative path:\t' + relativePath(dest_file, dest_mds_path))
        dest_set.add(os.path.basename(dest_file))

    if not (source_set == dest_set):
        print("mismatch in source and destination files. Make sure both old and new mds contains same files")
        exitScript(7)
    return


def checkForAttributeChange(source_node,dest_node):
    if set(source_node.attributes.items()) == set(dest_node.attributes.items()): #Check if both nodes have same set of key-value pairs then no need to compare or generate scritps
        return
    attr_set = set(list(source_node.attributes.keys()) + list(dest_node.attributes.keys()))
    if debug_flag >= DebugFlag.FINER : print printNode(source_node) + '  AttributeList: ',attr_set
    while(attr_set):
        attr = attr_set.pop()
        if source_node.hasAttribute(attr) and dest_node.hasAttribute(attr):
            if source_node.getAttribute(attr) == dest_node.getAttribute(attr):
                continue
            else:
                print 'Attribute Updated: '+attr+' modified from '+source_node.getAttribute(attr)+' to '+dest_node.getAttribute(attr)+'   '+printNode(source_node)
        elif source_node.hasAttribute(attr):
            print 'Attribute Removed: '+attr+' '+printNode(source_node)
        else:
            print  'Attribute Added: '+attr+' '+printNode(dest_node)
    return

    
def matchAndEliminateNode(to_visit,source_node_list,dest_node_list):
    temp_dest_list = []
    temp_source_list = []
    for dest_node in dest_node_list:
        for source_node in source_node_list:
            remove_node_flag = 0
            if (dest_node.nodeName == source_node.nodeName) and ( (source_node.hasAttribute('id') and dest_node.hasAttribute('id') and source_node.getAttribute("id") == dest_node.getAttribute("id")) or set(source_node.attributes.items()) == set(dest_node.attributes.items())):
                if dest_node.hasAttribute('id') or source_node.hasChildNodes or dest_node.hasChildNodes:
                    visit_node = (source_node,dest_node)
                    to_visit.insert(0,visit_node)
                temp_dest_list.append(dest_node)
                temp_source_list.append(source_node)
    try:
        for source_node in temp_source_list: source_node_list.remove(source_node)
        for dest_node in temp_dest_list: dest_node_list.remove(dest_node)
    except ValueError:
        print '################################################################################################'
        print '################ Error: Two Child with same set of attributes or With same ID ##################'
        print traceback.print_exc()
        print '################################################################################################'
    if source_node_list:
        printNodeList('Component Removed:',source_node_list)
    if dest_node_list:
        printNodeList('Component Added: ',dest_node_list)
    return


def modifiedDFS(to_visit):
    file_name = os.path.basename(curr_dest_file)
    index = string.find(file_name,'_Layout')
    file_name = file_name[:index]+'.jsff'
    print '\n\n\n************ Modifying : '+file_name+' ********************'
    while(to_visit):
        source_parent_node,dest_parent_node = to_visit.pop(0)
        source_child_node_list = copy.copy(source_parent_node.childNodes)
        dest_child_node_list = copy.copy(dest_parent_node.childNodes)
        source_child_node_list.reverse()
        dest_child_node_list.reverse()
        checkForAttributeChange(source_parent_node,dest_parent_node)
        matchAndEliminateNode(to_visit,source_child_node_list,dest_child_node_list)
    return


def processAndValidateScriptParameters():
    global source_mds_path,dest_mds_path,relative_recur_path
    Syntax = 'generateMain.py  old_mds_path  new_mds_path  dir_path_relative_to_mds'
    if not (len(sys.argv) ==4):
        print("Wrong arguement passed\n"+Syntax)
        exitScript(1)
    source_mds_path = sys.argv[1]
    if not os.path.exists(source_mds_path):
        print 'Source MDS Path Does not Exist: '+ source_mds_path
        exitScript(1)
    dest_mds_path = sys.argv[2]
    if not os.path.exists(dest_mds_path):
        print 'Destination MDS Path Does Not Exist : '+dest_mds_path
        exitScript(1)
    relative_recur_path = sys.argv[3]


def exitScript(n):
    print("exiting")
    sys.exit(n)


def initProcess():
    global curr_source_file,curr_dest_file,source_files,dest_files
    to_visit = []
    processAndValidateScriptParameters()
    prepareFileList()
    for curr_source_file, curr_dest_file in zip(source_files, dest_files):
        if not os.path.basename(curr_source_file) == os.path.basename(curr_dest_file):
            print("mismatch in source and destination files. Make sure both old and new mds contains same files")
            exitScript(4)
        else:
            source_dom = parse(curr_source_file)
            dest_dom = parse(curr_dest_file)
            source_root = source_dom.documentElement
            dest_root = dest_dom.documentElement
            visit_node = (source_root,dest_root)
            to_visit.append(visit_node)
            cleanDOM(source_root)
            cleanDOM(dest_root)
            modifiedDFS(to_visit)
    return

initProcess()