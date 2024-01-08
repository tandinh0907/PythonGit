import gitRepo
import os
import zlib
import hashlib
import sys
import collections
import gitSubObject

"""Reading and Writing GitObject section"""
def object_read(repo, inputObj):
    path = gitRepo.repo_file(repo, "objects", inputObj[0:2], inputObj[2:])

    if not os.path.isfile(path):
        return None

    with open (path, "rb") as f:
        raw = zlib.decompress(f.read())
        x = raw.find(b' ')
        fmt = raw[0:x]
        y = raw.find(b'\x00', x)
        size = int(raw[x:y].decode("ascii"))

        if size != len(raw)-y-1:
            raise Exception("Malformed object {0}: bad length".format(inputObj))

        match fmt:
            case b'commit' : c = gitSubObject.GitCommit
            case b'tree'   : c = gitSubObject.GitTree
            case b'tag'    : c = gitSubObject.GitTag
            case b'blob'   : c = gitSubObject.GitBlob
            case _:
                raise Exception("Unknown type {0} for object {1}".format(fmt.decode("ascii"), inputObj))

        return c(raw[y+1:])
    
def object_write(obj, repo=None):
    data = obj.serialize()
    result = obj.fmt + b' ' + str(len(data)).encode() + b'\x00' + data
    outputObj = hashlib.sha1(result).hexdigest()

    if repo:
        path = gitRepo.repo_file(repo, "objects", outputObj[0:2], outputObj[2:], mkdir=True)
        if not os.path.exists(path):
            with open(path, 'wb') as f:
                f.write(zlib.compress(result))
    return outputObj

def object_find(repo, name, fmt=None, follow=True):
    return name

def cat_file(repo, obj, fmt=None):
    obj = object_read(repo, object_find(repo, obj, fmt=fmt))
    sys.stdout.buffer.write(obj.serialize())

def object_hash(fd, fmt, repo=None):
    """ Hash object, writing it to repo if provided."""
    data = fd.read()

    match fmt:
        case b'commit' : obj = gitSubObject.GitCommit(data)
        case b'tree'   : obj = gitSubObject.GitTree(data)
        case b'tag'    : obj = gitSubObject.GitTag(data)
        case b'blob'   : obj = gitSubObject.GitBlob(data)
        case _: raise Exception("Unknown type %s!" % fmt)

    return object_write(obj, repo)

"""End of Reading and Writing GitObject section"""

"""Reading commit history: log section """
def kvlm_parse(rawMess, start=0, dct=None):
    if not dct:
        dct = collections.OrderedDict()

    # This function is recursive: it reads a key/value pair, then call
    # itself back with the new position.  So we first need to know
    # where we are: at a keyword, or already in the messageQ

    # We search for the next space and the next newline.
    spc = rawMess.find(b' ', start)
    nl = rawMess.find(b'\n', start)

    # If space appears before newline, we have a keyword.  Otherwise,
    # it's the final message, which we just read to the end of the file.

    # Base case
    # =========
    # If newline appears first (or there's no space at all, in which
    # case find returns -1), we assume a blank line.  A blank line
    # means the remainder of the data is the message.  We store it in
    # the dictionary, with None as the key, and return.
    if (spc < 0) or (nl < spc):
        assert nl == start
        dct[None] = rawMess[start+1:]
        return dct

    # Recursive case
    # ==============
    # we read a key-value pair and recurse for the next.
    key = rawMess[start:spc]

    # Find the end of the value.  Continuation lines begin with a
    # space, so we loop until we find a "\n" not followed by a space.
    end = start
    while True:
        end = rawMess.find(b'\n', end+1)
        if rawMess[end+1] != ord(' '): break

    # Grab the value
    # Also, drop the leading space on continuation lines
    value = rawMess[spc+1:end].replace(b'\n ', b'\n')

    # Don't overwrite existing data contents
    if key in dct:
        if type(dct[key]) == list:
            dct[key].append(value)
        else:
            dct[key] = [ dct[key], value ]
    else:
        dct[key]=value

    return kvlm_parse(rawMess, start=end+1, dct=dct)

def kvlm_serialize(keyMess):
    ans = b''

    # Output fields
    for k in keyMess.keys():
        # Skip the message itself
        if k == None: continue
        val = keyMess[k]
        # Normalize to a list
        if type(val) != list:
            val = [ val ]

        for v in val:
            ans += k + b' ' + (v.replace(b'\n', b'\n ')) + b'\n'

    # Append message
    ans += b'\n' + keyMess[None] + b'\n'

    return ans

#Using Graphviz for representing log
def log_graphviz(repo, inputObj, seen):

    if inputObj in seen:
        return
    seen.add(inputObj)

    commit = object_read(repo, inputObj)
    short_hash = inputObj[0:8]
    message = commit.kvlm[None].decode("utf8").strip()
    message = message.replace("\\", "\\\\")
    message = message.replace("\"", "\\\"")

    if "\n" in message: # Keep only the first line
        message = message[:message.index("\n")]

    print("  c_{0} [label=\"{1}: {2}\"]".format(inputObj, inputObj[0:7], message))
    assert commit.fmt==b'commit'

    if not b'parent' in commit.kvlm.keys():
        # Base case: the initial commit.
        return

    parents = commit.kvlm[b'parent']

    if type(parents) != list:
        parents = [ parents ]

    for p in parents:
        p = p.decode("ascii")
        print ("  c_{0} -> c_{1};".format(inputObj, p))
        log_graphviz(repo, p, seen)

"""End of Reading commit history: log section """

"""Reading commit data section"""
def tree_parse_one(raw, start=0):
    # Find the space terminator of the mode
    x = raw.find(b' ', start)
    assert x-start == 5 or x-start==6

    # Read the mode
    mode = raw[start:x]
    if len(mode) == 5:
        # Normalize to six bytes.
        mode = b" " + mode

    # Find the NULL terminator of the path
    y = raw.find(b'\x00', x)
    # and read the path
    path = raw[x+1:y]

    # Read the SHA and convert to a hex string
    obj = format(int.from_bytes(raw[y+1:y+21], "big"), "040x")
    return y+21, gitSubObject.GitTreeLeaf(mode, path.decode("utf8"), obj)

def tree_parse(raw):
    pos = 0
    max = len(raw)
    ans = list()
    while pos < max:
        pos, data = tree_parse_one(raw, pos)
        ans.append(data)

    return ans

#This is necessary to maintain git's indentity rule. 
def tree_leaf_sort_key(leaf):
    if leaf.mode.startswith(b"10"):
        return leaf.path
    else:
        return leaf.path + "/"
    
def tree_serialize(objt):
    objt.items.sort(key=tree_leaf_sort_key)
    ans = b''
    for i in objt.items:
        ans += i.mode
        ans += b' '
        ans += i.path.encode("utf8")
        ans += b'\x00'
        sha = int(i.obj, 16)
        ans += sha.to_bytes(20, byteorder="big")
    return ans