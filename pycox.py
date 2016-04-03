#!/usr/bin/env python
#---------------------------------------------------------------------------------------------------
#
# Script defines core operations on dropbox file system: list, remove, upload, download  etc.
#
#                                                                         v0 - Mar 31, 2016 - C.Paus
#---------------------------------------------------------------------------------------------------
import os,sys,subprocess,getopt,re,random,ConfigParser,pycurl,urllib,time,json,pprint
from io import BytesIO

#MY_ID = 

#===================================================================================================
#  H E L P E R S
#===================================================================================================
def testLocalSetup(action,src,tgt,debug=0):
    # The local setup needs a number of things to be present. Make sure all is there, or complain.

    # See whether we are setup
    base = os.environ.get('PYCOX_BASE')
    if base=='':
        print '\n ERROR -- pycox is not setup PYCOX_BASE environment not set.\n'
        sys.exit(1)

    # every action needs a source
    if src == '':
        print '\n ERROR - no source specified. EXIT!\n'
        print usage
        sys.exit(1)

    # some actions need a target
    if action == 'up' or action == 'down' or action == 'cp' or action == 'mv':
        if tgt == '':
            print '\n ERROR - no target specified. EXIT!\n'
            print usage
            sys.exit(1)
    return

def buildCurlOptions(config):
    # here we just convert the oauth config menu to a dictionary for curl parameters

    postData = {}
    for (key,value) in config.items('oauth'):
        postData['oauth_'+key] = value
    # add the time and a random number
    postData['oauth_timestamp'] = time.time()
    postData['oauth_nonce'] = 1234512
    postfields = urllib.urlencode(postData)

    return postfields

def dbxBaseUrl(config,api,src,debug=0):
    # this is the generic interface to constructa full curl URL based on put (default)
    
    # build the curl url
    url = config.get('api',api) + '/' + config.get('general','access_level')

    # add source is not empty
    if src != '':
        srcUrl = urllib.quote_plus(src)
        url += '/' + srcUrl

    # prepare the curl authentication parameters
    postfields = buildCurlOptions(config)

    url += '?' + postfields

    return url

def dbxBaseUrlGet(config,api,src,debug=0):
    # this is the generic interface to constructa full curl URL based on get (default is put)
   
    # build the curl url
    url = config.get('api',api)

    # prepare the curl authentication parameters
    srcUrl = urllib.quote_plus(src)
    postfields  = buildCurlOptions(config)
    postfields += '&root=' + config.get('general','access_level')
    postfields += '&path=' + srcUrl
    
    return (url,postfields)

def dbxExecuteCurl(url,postfields='',fileName='',debug=0):
    # execute a well defined curl command and return the json formatted output data

    # setup the curl output buffer
    header = BytesIO()
    body = BytesIO()

    # define our curl request
    c = pycurl.Curl()
    c.setopt(c.URL,url)
    c.setopt(c.HEADERFUNCTION,header.write)
    c.setopt(c.WRITEFUNCTION,body.write)

    # is this a 'get' request?
    if postfields != '':
        c.setopt(c.POSTFIELDS,postfields)

    # uploading a file?
    fileH = None           # make sure it does not go out of scope
    if fileName != '':
        fileSize = os.path.getsize(fileName)
        fileH = open(fileName,'rb')
        c.setopt(pycurl.UPLOAD,1)
        c.setopt(c.READFUNCTION,fileH.read)
        c.setopt(c.INFILESIZE,fileSize)
        print  ' File: %s  size: %d bytes'%(fileName,fileSize) 

    # perform the curl request and close it
    c.perform()
    c.close()

    # extract the data from the curl buffer using a json structure
    data = {}
    #print body.getvalue()
    try:
        data = json.loads(body.getvalue())
    except ValueError:
        # data seem empty 
        print ' ERROR - ValueError -- dbxExecuteCurl: ' + url

    if debug>2:
        pprint.pprint(data)

    return data

def dbxExecuteCurlToFile(url,fileName,debug=0):
    # execute a well defined curl command and return the json formatted output data

    # setup the curl output buffer
    with open(fileName,'wb') as fileH:
        # define our curl request
        c = pycurl.Curl()
        c.setopt(c.URL,url)
        c.setopt(c.WRITEDATA,fileH)
    
        # perfrom the curl request and close it
        c.perform()
        print 'Status: %d (in %f secs)' %(c.getinfo(c.RESPONSE_CODE),c.getinfo(c.TOTAL_TIME))

        c.close()

    return

def dbxGetMetaData(config,src,debug=0):
    # this is the generic interface to extract the metadata of a given 'path' (= src)

    # get the core elements for curl
    url = dbxBaseUrl(config,'metadata_url',src,debug)
    data = dbxExecuteCurl(url,'','',debug)

    return data

def dbxIsDir(config,src,debug=0):
    # Test whether path is directory (0 - not directory, 1 - is directory, -1 - inquery failed)

    # setup the curl output buffer
    data = dbxGetMetaData(config,src,debug)

    # loop through the content and show each entry we find
    if 'path' in data:
        if 'is_deleted' in data:
            if data["is_deleted"]:
                return -1
        if data["is_dir"]:
            return 1
    else:
        if debug:
            print ' ERROR - Requested object not identified.'
        return -1
        
    return 0

def dbxLs(config,src,debug=0):
    # List the given source

    print "# o List o  " + src
    
    # setup the curl output buffer
    data = dbxGetMetaData(config,src,debug)
    
    # make sure path exists
    if 'is_deleted' in data:
        entryIsDeleted = data["is_deleted"]
        if entryIsDeleted:
            print ' ERROR - path does not exist (is_deleted)'

    # loop through the content and show each entry we find
    if 'contents' in data:
        for entry in data["contents"]:
            entryPath = entry["path"]
            entrySize = entry["bytes"]
            entryType = 'F'
            if entry["is_dir"]:
                entryType = 'D'
            print '%s:%d %s'%(entryType,entrySize,entryPath)
    else:
        if 'path' in data:
            entryPath = data["path"]
            entrySize = data["bytes"]
            entryIsDeleted = data["is_deleted"]
            entryType = 'F'
            if data["is_dir"]:
                entryType = 'D'
            if entryIsDeleted:
                print ' ERROR - file does not exist (is_deleted)'
            else:
                print '%s:%d %s'%(entryType,entrySize,entryPath)
        else:
            print ' ERROR - Requested object does not exist.'

    return

def dbxDu1(config,src,debug=0):
    # List disk usage for the given entry but only at most 1 level deep (for directories)

    print "# o DiskUsage -1 o  " + src
    
    # setup the curl output buffer
    data = dbxGetMetaData(config,src,debug)

    # loop through the content and show each entry we find
    totalBytes = 0
    if 'contents' in data:
        for entry in data["contents"]:
            entryPath = entry["path"]
            entrySize = entry["bytes"]
            entryType = 'F'
            if entry["is_dir"]:
                entryType = 'D'
            if debug>1:
                print '%s:%d %s'%(entryType,entrySize,entryPath)
            totalBytes += entrySize
    else:
        if 'path' in data:
            entryPath = data["path"]
            entrySize = data["bytes"]
            entryType = 'F'
            if data["is_dir"]:
                entryType = 'D'
            if debug>1:
                print '%s:%d %s'%(entryType,entrySize,entryPath)
            totalBytes = entrySize
        else:
            print ' ERROR - Requested object does not exist.'
            totalBytes = 0

    # summarize our findings
    print ' %s %.3f'%('Total [GB]:',totalBytes/1000./1000./1000.)

    return

def dbxUp(config,src,tgt,debug=0):
    # upload a given local source file (src) to dropbox target file (tgt)

    print "# o Upload o  " + src + "  -->  " + tgt

    # size determines whether in one shot or by chunks
    statinfo = os.stat(src)
    size = statinfo.st_size
  
    if size > 157286000:
        dbxUpChunked(config,src,tgt,debug=0):    
    else:
        # get the core elements for curl
        url = dbxBaseUrl(config,'upload_url',tgt,debug)
        data = dbxExecuteCurl(url,'',src,debug)

    return

def createChunk(src,tmpChunkFile,offsetBytes,chunkSize,debug):
    # create a chunk of a file starting at offset and chunksize large if possible
    
    # convert to MB (for chunk file)
    offsetMBytes=offsetBytes/1024/1024
    cmd = "dd if=" + src " of=" + tmpChunkFile + " bs=1048576 skip=" + offsetMBytes \
        + " count=" + chunkSize + " 2> /dev/null"

    return

def dbxUpChunked(config,src,tgt,debug=0):
    # upload a given large local source file (src) to dropbox target file (tgt) as the chances
    # for failure are large, the upload is done in chunks and later committed. Dropbox seems to
    # be checking.

    print "# o UploadChunked o  " + src + "  -->  " + tgt

    # get the core elements for curl
    offestBytes = 0
    uploadId = 0
    tmpChunkFile = "/tmp/pycox_chunk." + MY_ID
    while offestBytes!= size:

        # make the temporary chunk file
        createChunk(src,tmpChunkFile,offsetBytes,chunkSize,debug)

        # first request should not have those parameters
        parameters = ''
        if offsetBytes != 0:
            parameters="upload_id=" + uploadId + "&offset=" + offsetBytes
            
        # 
        url = dbxBaseUrl(config,'chunked_upload_url',tgt,debug)
        data = dbxExecuteCurl(url,'',tmpChunkFile,debug)

#chunked_upload_url = https://api-content.dropbox.com/1/chunked_upload
#chunked_upload_commit_url = https://api-content.dropbox.com/1/commit_chunked_upload

    return

def dbxDown(config,src,tgt,debug=0):
    # upload a given local source file (src) to dropbox target file (tgt)

    print "# o Download o  " + src + "  -->  " + tgt

    # get the core elements for curl
    url = dbxBaseUrl(config,'download_url',src,debug)
    data = dbxExecuteCurlToFile(url,tgt,debug)

    return

def dbxRm(config,src,debug=0):
    # Remove the given path if it is a file

    print "# o RemoveFile o  " + src

    isDir = dbxIsDir(config,src,debug)

    if   isDir == 0:
        # get the core elements for curl
        (url,postfields) = dbxBaseUrlGet(config,'delete_url',src,debug)

        print " URL: " + url
        print " POSTFIELDS: " + postfields

        data = dbxExecuteCurl(url,postfields,'',debug)
    elif isDir == 1:
        print ' ERROR - path is a directory, cannot delete.'
    else:
        print ' ERROR - path inquery failed.'
 
    return

def dbxRmDir(config,src,debug=0):
    # Remove the given path if it is a directory (show contents and ask for confirmation)

    print "# o RemoveDir o  " + src

    isDir = dbxIsDir(config,src,debug)

    if   isDir == 1:
        # show what is in there and ask
        print ''
        dbxLs(config,src,debug)
        print '\n Do you really want to delete this directory?'
        response = raw_input(" Please confirm [N/y]: ") 
        if response == 'y':
            # get the core elements for curl
            (url,postfields) = dbxBaseUrlGet(config,'delete_url',src,debug)
            data = dbxExecuteCurl(url,postfields,'',debug)
        else:
            print "\n STOP. EXIT here. \n"
            
    elif isDir == 0:
        print ' ERROR - path is a file, cannot delete.'
    else:
        print ' ERROR - path inquery failed.'
 
    return

def dbxMkDir(config,src,debug=0):
    # Make given path as a directory

    print "# o MakeDir o  " + src

    isDir = dbxIsDir(config,src,debug)

    if   isDir == 1:
        print ' ERROR - path is a directory and exists already.'
    elif isDir == 0:
        print ' ERROR - path is a file, cannot make a same name directory.'
    else:
        # show what is in there and ask
        # get the core elements for curl
        (url,postfields) = dbxBaseUrlGet(config,'mkdir_url',src,debug)
        data = dbxExecuteCurl(url,postfields,'',debug)

    return

#===================================================================================================
#  M A I N
#===================================================================================================
# Define string to explain usage of the script
usage =  " Usage: pycox.py  --action=<what do you want to do?>\n"
usage += "                  --source=<the source the action should apply to>\n"
usage += "                [ --target=<the target where data should go> ]\n"
usage += "                [ --debug=0 ]             <-- see various levels of debug output\n"
usage += "                [ --exec ]                <-- add this to execute all actions\n"
usage += "                [ --help ]\n"

# Define the valid options which can be specified and check out the command line
valid = ['configFile=','action=','source=','target=','debug=','exec','help']
try:
    opts, args = getopt.getopt(sys.argv[1:], "", valid)
except getopt.GetoptError, ex:
    print usage
    print str(ex)
    sys.exit(1)

# --------------------------------------------------------------------------------------------------
# Get all parameters for the production
# --------------------------------------------------------------------------------------------------
# Set defaults for each command line parameter/option
configFile = os.environ.get('PYCOX_BASE') + '/' + 'pycox.cfg'
testFile = os.environ.get('HOME') + '/' + '.pycox.cfg'
if os.path.isfile(testFile):
    configFile = testFile

action = 'ls'
src = ''
tgt = ''
exe = False
debug = 0

# Read new values from the command line
for opt, arg in opts:
    if   opt == "--help":
        print usage
        sys.exit(0)
    elif opt == "--action":
        action = arg
    elif opt == "--configFile":
        configFile = arg
    elif opt == "--source":
        src = arg
    elif opt == "--target":
        tgt = arg
    elif opt == "--debug":
        debug = int(arg)
    elif opt == "--exec":
        exe = True

# inspecting the local setup
#---------------------------
testLocalSetup(action,src,tgt,debug)

# Read the configuration file
#----------------------------
config = ConfigParser.RawConfigParser()
config.read(configFile)

# looks like we have a valid request
#-----------------------------------
if action == 'ls':
    dbxLs(config,src,debug)
elif action == 'rm':
    dbxRm(config,src,debug)
elif action == 'rmdir':
    dbxRmDir(config,src,debug)
elif action == 'mkdir':
    dbxMkDir(config,src,debug)
elif action == 'du1':
    dbxDu1(config,src,debug)
elif action == 'up':
    dbxUp(config,src,tgt,debug)
elif action == 'down':
    dbxDown(config,src,tgt,debug)
else:
    print "\nAction is undefined: " + action + "\n"
