import gitRepo
import os
import zlib
import hashlib
import sys
import collections
import gitSubObject
import re

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

#More presice, the name resolution function will work like below:
#   _If name is HEAD, it will just resolve .git/HEAD;
#   _If name is a full hash, this hash is returned unmodified.
#   _If name looks like a short hash, it will collect objects whose full hash begin with this short hash.
#   _At last, it will resolve tags and branches matching name.
def object_resolve(repo, name):
    candidates = list()
    hashRE = re.compile(r"^[0-9A-Fa-f]{4,40}$")
    # Empty string?  Abort.
    if not name.strip():
        return None
    # Head is nonambiguous
    if name == "HEAD":
        return [ ref_resolve(repo, "HEAD") ]
    # If it's a hex string, try for a hash.
    if hashRE.match(name):
        # This may be a hash, either small or full.  4 seems to be the
        # minimal length for git to consider something a short hash.
        # This limit is documented in man git-rev-parse
        name = name.lower()
        prefix = name[0:2]
        path = gitRepo.repo_dir(repo, "objects", prefix, mkdir=False)
        if path:
            rem = name[2:]
            for f in os.listdir(path):
                if f.startswith(rem):
                    # Notice a string startswith() itself, so this
                    # works for full hashes.
                    candidates.append(prefix + f)
    # Try for references.
    as_tag = ref_resolve(repo, "refs/tags/" + name)
    if as_tag: # Did we find a tag?
        candidates.append(as_tag)
    as_branch = ref_resolve(repo, "refs/heads/" + name)
    if as_branch: # Did we find a branch?
        candidates.append(as_branch)
    return candidates

#This function take in a name will return a complete SHA-1 hash.
#It will work as below:
#   _If we have a tag and fmt is anything else, we follow the tag.
#   _If we have a commit and fmt is tree, we return this commit’s tree object
#   _In all other situations, we bail out: nothing else makes sense.
def object_find(repo, name, fmt=None, follow=True):
    sha = object_resolve(repo, name)
    if not sha:
        raise Exception("No such reference {0}.".format(name))
    if len(sha) > 1:
        raise Exception("Ambiguous reference {0}: Candidates are:\n - {1}.".format(name,  "\n - ".join(sha)))
    sha = sha[0]
    if not fmt:
        return sha
    while True: 
        obj = object_read(repo, sha)
        if obj.fmt == fmt:
            return sha
        if not follow:
            return None
        if obj.fmt == b'tag':
            sha = obj.kvlm[b'object'].decode("ascii")
        elif obj.fmt == b'commit' and fmt == b'tree':
                sha = obj.kvlm[b'tree'].decode("ascii")
        else:
              return None

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
    
def tree_serialize(obj):
    obj.items.sort(key=tree_leaf_sort_key)
    ans = b''
    for i in obj.items:
        ans += i.mode
        ans += b' '
        ans += i.path.encode("utf8")
        ans += b'\x00'
        sha = int(i.sha, 16)
        ans += sha.to_bytes(20, byteorder="big")
    return ans

def ls_tree(repo, ref, recursive=None, prefix=""):
    sha = object_find(repo, ref, fmt=b"tree")
    obj = object_read(repo, sha)
    for item in obj.items:
        if len(item.mode) == 5:
            type = item.mode[0:1]
        else:
            type = item.mode[0:2]

        match type: # Determine the type.
            case b'04': type = "tree"
            case b'10': type = "blob" # A regular file.
            case b'12': type = "blob" # A symlink. Blob contents is link target.
            case b'16': type = "commit" # A submodule
            case _: raise Exception("Weird tree leaf mode {}".format(item.mode))

        if not (recursive and type=='tree'): # This is a leaf
            print("{0} {1} {2}\t{3}".format(
                "0" * (6 - len(item.mode)) + item.mode.decode("ascii"),
                # Git's ls-tree displays the type
                # of the object pointed to.  We can do that too :)
                type,
                item.sha,
                os.path.join(prefix, item.path)))
        else: # This is a branch, recurse
            ls_tree(repo, item.sha, recursive, os.path.join(prefix, item.path))
    
def tree_checkout(repo, tree, path):
    for item in tree.items:
        obj = object_read(repo, item.sha)
        dest = os.path.join(path, item.path)
        if obj.fmt == b'tree':
            os.mkdir(dest)
            tree_checkout(repo, obj, dest)
        elif obj.fmt == b'blob':
            with open(dest, 'wb') as f:
                f.write(obj.blobdata)

"""End of reading commit data section"""

"""Git Reference, Tags, and Branches Section"""

#we define ref as text files, in the .git/refs hierarchy.
#They hold the SHA-1 identifier of an object, or a reference to another reference, ultimately to a SHA-1 (no loops!)

#We call: reference on the form ref: path/to/other/ref and indirect ref.
#         reference with SHA1-objectID a direct ref. 

#This function is a simple recursive solver that will take a ref name 
#as well as its indirect reference in the form of path/to/other/ref
#and return a SHA-1 identifier
def ref_resolve(repo, ref):
    path = gitRepo.repo_file(repo, ref)
    if not os.path.isfile(path):
        return None
    with open(path, 'r') as fp:
        data = fp.read()[:-1]
    if data.startswith("ref: "):
        return ref_resolve(repo, data[5:])
    else:
        return data

#This function list all references in a repository sorted similar to actual Git
def ref_list(repo, path=None):
    if not path:
        path = gitRepo.repo_dir(repo, "refs")
    ret = collections.OrderedDict()
    for f in sorted(os.listdir(path)):
        can = os.path.join(path, f)
        if os.path.isdir(can):
            ret[f] = ref_list(repo, can)
        else:
            ret[f] = ref_resolve(repo, can)

    return ret

def show_ref(repo, refs, with_hash=True, prefix=""):
    for k, v in refs.items():
        if type(v) == str:
            print ("{0}{1}{2}".format(
                v + " " if with_hash else "",
                prefix + "/" if prefix else "",
                k))
        else:
            show_ref(repo, v, with_hash=with_hash, prefix="{0}{1}{2}".format(prefix, "/" if prefix else "", k))

#The most simple use of refs is tags. A tag is just a user-defined name for an object, often a commit.
#One of the common use of tag is for identifying software releasing.
#Tags are actually ref. They live in the .git/refs/tags/ hierarchy.
#We commonly use 2 type of tags: lightweight tags and tags objects.
#Lightweight tags: regular refs to a commit, a tree or a blob.
#Tag objects: regular ref poiting to an object type tags. 
#Tag objects have an author, a date, optional PGP signature, and optional notation.
#Tag objects's format is the same as a commit object.
            
def tag_create(repo, name, ref, create_tag_object = False):
    sha = object_find(repo, ref)
    if create_tag_object:
        tag = gitSubObject.GitTag(repo)
        tag.kvlm = collections.OrderedDict()
        tag.kvlm[b'object'] = sha.encode()
        tag.kvlm[b'type'] = b'commit'
        tag.kvlm[b'tag'] = name.encode()
        tag.kvlm[b'tagger'] = b'Wyag <tandinh0907@gmail.com>'
        tag.kvlm[None] = b"A tag generated by wyag"
        tag_sha = object_write(tag)
        ref_create(repo, "tags/" + name, tag_sha)
    else:
        ref_create(repo, "tags/" + name, sha)

def ref_create(repo, ref_name, sha):
    with open(gitRepo.repo_file(repo, "refs/" + ref_name), 'w') as fp:
        fp.write(sha + "\n")

#Now, what is a branch? Simply, a branch is a reference to a commit. 
#Some could even say that a branch is a kind of a name for a commit.
#Tags are refs that live in .git/refs/tags, branches are refs that live in .git/refs/heads.
#Of course there are some differences between a branche and a tag:
#   _Branches are references to a commit, tags can refer to any object;
#   _Most importantly, the branch ref is updated at each commit. Means for every commit:
#       *a new commit object is created, with the current branch’s (commit!) ID as its parent;
#       *the commit object is hashed and stored;
#       *the branch ref is updated to refer to the new commit’s hash.        

"""End of Git Reference, Tags, and Branches Section"""

