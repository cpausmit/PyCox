#!/usr/bin/env python
#---------------------------------------------------------------------------------------------------
#
# Script defines core operations on dropbox file system: list, remove, upload, download  etc.
#
#                                                                         v0 - Mar 31, 2016 - C.Paus
#---------------------------------------------------------------------------------------------------
import os,sys,subprocess,getopt,re,random,ConfigParser,pycurl,urllib,time,json,pprint
from io import BytesIO

# Make a unique id to be used throughout to generate unique files (the id
# is not guaranteed to be unique but it is hard to duplicate it.)
MY_ID = int(time.time()*100)
#print "My ID: %d"%(MY_ID)

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

    # add the time and a random number [ this might not be needed at all to be checked ]
    postData['oauth_timestamp'] = int(time.time())
    postData['oauth_nonce'] = str(MY_ID)

    # convert data dictionary into a url encoded string
    postfields = urllib.urlencode(postData)

    return postfields

def dbxBaseUrl(config,api,src,debug=0):
    # this is the generic interface to constructa full curl URL based on put (default)
    
    # build the curl url
    url = config.get('api',api)

    # some urls do not need the access level added
    if api != 'chunked_upload_url':
        url += '/' + config.get('general','access_level')

    # add source if it is not empty
    if src != '':
        srcUrl = urllib.quote_plus(src)
        url += '/' + srcUrl

    # prepare the curl authentication parameters
    postfields = buildCurlOptions(config)

    url += '?' + postfields

    return url

def dbxBaseUrlGet(config,api,debug=0):
    # this is the generic interface to construct a full curl URL based on get (default is put)
   
    # build the curl url
    url = config.get('api',api)

    # prepare the curl authentication parameters
    postfields  = buildCurlOptions(config)
    postfields += '&root=' + config.get('general','access_level')
    
    return (url,postfields)

def dbxExecuteCurl(url,postfields='',fileName='',debug=0):
    # execute a well defined curl command and return the json formatted output data

    # setup the curl output buffer
    header = BytesIO()
    body = BytesIO()

    # define our curl request
    c = pycurl.Curl()
    if debug>1:
        print ' URL: ' + url
    c.setopt(c.URL,url)
    c.setopt(c.HEADERFUNCTION,header.write)
    c.setopt(c.WRITEFUNCTION,body.write)

    # is this a 'get' request?
    if postfields != '':
        if debug>1:
            print ' POSTFIELDS: ' + postfields
        c.setopt(c.POSTFIELDS,postfields)

    # uploading a file?
    fileH = None           # make sure it does not go out of scope
    if fileName != '':
        fileSize = os.path.getsize(fileName)
        fileH = open(fileName,'rb')
        c.setopt(pycurl.UPLOAD,1)
        c.setopt(c.READFUNCTION,fileH.read)
        c.setopt(c.INFILESIZE,fileSize)
        if debug>0:
            print  ' File: %s  size: %d bytes'%(fileName,fileSize) 

    # perform the curl request and close it
    c.perform()
    c.close()

    # extract the data from the curl buffer using a json structure
    data = {}
    try:
        data = json.loads(body.getvalue())
        if debug>2:
            pprint.pprint(data)
    except ValueError:
        # data seem empty 
        print ' ERROR - ValueError -- dbxExecuteCurl URL:    ' + url
        print '                    -- dbxExecuteCurl FIELDS: ' + postfields

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
            entryIsDeleted = False
            if 'is_deleted' in data:
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

    if debug>-1:
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
    if debug>-1:
        print ' %s %.3f'%('Total [GB]:',totalBytes/1000./1000./1000.)

    return totalBytes

def dbxDu2(config,src,debug=0):
    # List disk usage for the given entry but only at most 2 level deep (for directories)

    print "# o DiskUsage -2 o  " + src

    spaceSubdirs = { src : 0 }
    
    # setup the curl output buffer
    data = dbxGetMetaData(config,src,debug)

    # loop through the content
    totalBytes = 0
    if 'contents' in data:
        for entry in data["contents"]:
            entryPath = entry["path"]
            entrySize = entry["bytes"]
            entryType = 'F'
            if entry["is_dir"]:
                entryType = 'D'
                spaceSubdirs[entryPath] = 0
            if debug>1:
                print '%s:%d %s'%(entryType,entrySize,entryPath)
            #totalBytes += entrySize
    else:
        if 'path' in data:
            entryPath = data["path"]
            entrySize = data["bytes"]
            entryType = 'F'
            if data["is_dir"]:
                entryType = 'D'
                spaceSubdirs[entryPath] = 0
            if debug>1:
                print '%s:%d %s'%(entryType,entrySize,entryPath)
            #totalBytes = entrySize
        else:
            print ' ERROR - Requested object does not exist.'
            #totalBytes = 0

    # loop through the sub directories and add
    for key, value in spaceSubdirs.items():
        sizeBytes = dbxDu1(config,key,-1)
        spaceSubdirs[key] += sizeBytes
        totalBytes += sizeBytes

        print ' %.3f -- %s'%(sizeBytes/1000./1000./1000.,key)

    # summarize our findings
    print ' %.3f == %s'%(totalBytes/1000./1000./1000.,'Total [GB]')

    return
    
def dbxCp(config,src,tgt,debug=0):
    # copy a given remote source file (src) to remote target file (tgt)

    print "# o Copy o  " + src + "  -->  " + tgt

    # check if target is an existing directory and adjust accordingly
    isSrcDir = dbxIsDir(config,src,debug)
    isTgtDir = dbxIsDir(config,tgt,debug)

    if isTgtDir == 1:
        f = src.split("/")
        baseFile = f.pop()
        tgt += '/' + baseFile

    if isSrcDir == 0 and isTgtDir == 0:                   # this means source and target files exist
        # we need to delete the target first as it will otherwise cause an error
        dbxRm(config,tgt,debug)        
    
    # build the url
    (url,postfields) = dbxBaseUrlGet(config,'copy_url',debug)
    postfields += '&from_path=' + urllib.quote_plus(src)
    postfields += '&to_path=' + urllib.quote_plus(tgt)

    # execute
    data = dbxExecuteCurl(url,postfields,'',debug)

    if 'error' in data:
        print ' ERROR - ExecutionError -- dbxCp URL:    ' + url
        print '                        -- dbxCp FIELDS: ' + postfields
        print '         ' + data['error']

    return

def dbxMv(config,src,tgt,debug=0):
    # move a given remote source file (src) to remote target file (tgt)

    print "# o Move o  " + src + "  -->  " + tgt

    # check if target is an existing directory and adjust accordingly
    isSrcDir = dbxIsDir(config,src,debug)
    isTgtDir = dbxIsDir(config,tgt,debug)

    if isTgtDir == 1:
        f = src.split("/")
        baseFile = f.pop()
        tgt += '/' + baseFile

    if isSrcDir == 0 and isTgtDir == 0:                   # this means source and target files exist
        # we need to delete the target first as it will otherwise cause an error
        dbxRm(config,tgt,debug)

    # build the url
    (url,postfields) = dbxBaseUrlGet(config,'move_url',debug)
    postfields += '&from_path=' + urllib.quote_plus(src)
    postfields += '&to_path=' + urllib.quote_plus(tgt)

    # execute
    data = dbxExecuteCurl(url,postfields,'',debug)

    if 'error' in data:
        print ' ERROR - ExecutionError -- dbxMv URL:    ' + url
        print '                        -- dbxMv FIELDS: ' + postfields
        print '         ' + data['error']

    return
    
def dbxUp(config,src,tgt,debug=0):
    # upload a given local source file (src) to dropbox target file (tgt)

    print "# o Upload o  " + src + "  -->  " + tgt

    # size determines whether in one shot or by chunks
    statinfo = os.stat(src)
    size = statinfo.st_size
  
    if size > 157286000:
        dbxUpChunked(config,src,tgt,debug=0)
    else:
        # get the core elements for curl
        url = dbxBaseUrl(config,'upload_url',tgt,debug)
        data = dbxExecuteCurl(url,'',src,debug)

        if 'error' in data:
            print ' ERROR - ExecutionError -- dbxUp URL:    ' + url
            print '                        -- dbxUp FIELDS: ' + ''
            print '         ' + data['error']

    return

def createChunk(src,tmpChunkFile,offsetBytes,chunkSizeMbytes,debug):
    # create a chunk of a file starting at offset and chunksize large if possible
    
    # convert to MB (for chunk file)
    offsetMBytes = offsetBytes/1024/1024
    cmd  = "dd if=" + src + " of=" + tmpChunkFile + " skip=" + str(offsetMBytes)
    cmd += " bs=1048576 count=" + str(chunkSizeMbytes) + " 2> /dev/null"
    if debug>1:
        print " CMD: " + cmd
    os.system(cmd)

    return

def removeChunk(tmpChunkFile,debug):
    # remove the temporary chunk
    
    os.remove(tmpChunkFile)

    return

def nextChunkedUpload(uploadId,offsetBytes,data,debug):
    # create a chunk of a file starting at offset and chunksize large if possible
    
    if 'upload_id' in data:
        error = 0
        uploadId = data['upload_id']
        offsetBytes = data['offset']
    elif 'error' in data:
        # in case of error keep offsetBytes the same so to make another try
        error = 1
        print ' ERROR - ' + data['error']

    if debug>2:
        pprint.pprint(data)
    
    return (uploadId, offsetBytes, error)

def dbxUpChunked(config,src,tgt,debug=0):
    # upload a given large local source file (src) to dropbox target file (tgt) as the chances
    # for failure are large, the upload is done in chunks and later committed. Dropbox seems to
    # be checking.

    if debug>1:
        print "# o UploadChunked o  " + src + "  -->  " + tgt

    # size determines whether in one shot or by chunks
    statinfo = os.stat(src)
    size = statinfo.st_size

    if debug>0:
        print "#   Size [GB]: %.3f "%(size/1000/1000/1000)

    # get the core elements for curl
    nErrors = 0      # keep track of potential upload errors
    nErrorsMax = config.get('general','chunk_error_max')
    offsetBytes = 0  # used to keep track of progress
    uploadId = 0     # will be set by dropbox and returned on first chunk
    tmpChunkFile = "/tmp/pycox_tmp_chunk." + str(MY_ID)
    chunkSizeMbytes = config.get('general','chunk_size_mbytes')
    
    # be aware of the fact that there is no error handling yet, NEEDS TO BE IMPLEMENTED
    while offsetBytes != size:

        # make the temporary chunk file
        createChunk(src,tmpChunkFile,offsetBytes,chunkSizeMbytes,debug)

        # first request should not have those parameters
        parameters = ''
        if offsetBytes != 0:
            parameters="upload_id=" + str(uploadId) + "&offset=" + str(offsetBytes)
            
        # build the url carefully
        url  = dbxBaseUrl(config,'chunked_upload_url','',debug)
        url += '&' + parameters
        data = dbxExecuteCurl(url,'',tmpChunkFile,debug)
        
        # read the uploadId and new offset from dropbox
        (uploadId, offsetBytes, error) = nextChunkedUpload(uploadId,offsetBytes,data,debug)
        if error>0:
            nErrors += 1
            if nErrors >= nErrorsMax:
                print '\n ERROR - chunk in chunked upload failed %d times, giving up.\n'%(nErrors)
                sys.exit(1)
            
        # remove temporary chunk file
        removeChunk(tmpChunkFile,debug)

    # chunks are now all uploaded (no errors) -- commit the file
    nErrors = 0      # keep track of potential upload commit errors
    while True:
        # build the url here locally, non-standard
        url = config.get('api','chunked_upload_commit_url') \
            + '/' + config.get('general','access_level') \
            + '/' + urllib.quote_plus(tgt)
        postfields = 'upload_id=' + str(uploadId) + '&' + buildCurlOptions(config)

        if debug>1:
            print " URL:        " + url
            print " Postfields: " + postfields

        data = dbxExecuteCurl(url,postfields,'',debug)

        # deal with error
        if 'error' in data:
            nErrors += 1
            if nErrors >= nErrorsMax:
                print '\n ERROR - commit of chunked upload failed %d times, giving up.\n'%(nErrors)
                sys.exit(1)
        else:
            break
        
    return

def dbxDown(config,src,tgt,debug=0):
    # upload a given local source file (src) to dropbox target file (tgt)

    print "# o Download o  " + src + "  -->  " + tgt

    # get the core elements for curl
    url = dbxBaseUrl(config,'download_url',src,debug)
    dbxExecuteCurlToFile(url,tgt,debug)

    return

def dbxRm(config,src,debug=0):
    # Remove the given path if it is a file

    print "# o RemoveFile o  " + src

    isDir = dbxIsDir(config,src,debug)

    if   isDir == 0:
        # get the core elements for curl
        (url,postfields) = dbxBaseUrlGet(config,'delete_url',debug)
        postfields += '&path=' + urllib.quote_plus(src)
        data = dbxExecuteCurl(url,postfields,'',debug)
        if 'error' in data:
            print ' ERROR - ExecutionError -- dbxRm URL:    ' + url
            print '                        -- dbxRm FIELDS: ' + postfields
            print '         ' + data['error']

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
            (url,postfields) = dbxBaseUrlGet(config,'delete_url',debug)
            postfields += '&path=' + urllib.quote_plus(src)
            data = dbxExecuteCurl(url,postfields,'',debug)
            if 'error' in data:
                print ' ERROR - ExecutionError -- dbxRm URL:    ' + url
                print '                        -- dbxRm FIELDS: ' + postfields
                print '         ' + data['error']
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
        print ' INFO - path is a directory and exists already.'
    elif isDir == 0:
        print ' ERROR - path is a file, cannot make a same name directory.'
    else:
        # show what is in there and ask
        # get the core elements for curl
        (url,postfields) = dbxBaseUrlGet(config,'mkdir_url',debug)
        postfields += '&path=' + urllib.quote_plus(src)
        data = dbxExecuteCurl(url,postfields,'',debug)
        if 'error' in data:
            print ' ERROR - ExecutionError -- dbxMkdir URL:    ' + url
            print '                        -- dbxMkdir FIELDS: ' + postfields
            print '         ' + data['error']

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
if   action == 'ls':
    dbxLs(config,src,debug)
elif action == 'rm':
    dbxRm(config,src,debug)
elif action == 'rmdir':
    dbxRmDir(config,src,debug)
elif action == 'mkdir':
    dbxMkDir(config,src,debug)
elif action == 'du1':
    dbxDu1(config,src,debug)
elif action == 'du2':
    dbxDu2(config,src,debug)
elif action == 'cp':
    dbxCp(config,src,tgt,debug)
elif action == 'mv':
    dbxMv(config,src,tgt,debug)
elif action == 'up':
    dbxUp(config,src,tgt,debug)
elif action == 'down':
    dbxDown(config,src,tgt,debug)
else:
    print "\nAction is undefined: " + action + "\n"
