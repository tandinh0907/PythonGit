import gitUtil

class GitObject (object):

    def __init__(self, data=None):
        if data != None:
            self.deserialize(data)
        else:
            self.init()

    def serialize(self, repo):
        raise Exception("Unimplemented!")

    def deserialize(self, data):
        raise Exception("Unimplemented!")

    def init(self):
        pass 

class GitBlob(GitObject):
    fmt=b'blob'

    def serialize(self):
        return self.blobdata

    def deserialize(self, data):
        self.blobdata = data

class GitCommit(GitObject):
    fmt=b'commit'

    def init(self):
        self.kvlm = dict()

    def deserialize(self, data):
        self.kvlm = gitUtil.kvlm_parse(data)

    def serialize(self):
        return gitUtil.kvlm_serialize(self.kvlm)
    
class GitTreeLeaf (object):
    def __init__(self, mode, path, sha):
        self.mode = mode
        self.path = path
        self.sha = sha

class GitTree(GitObject):
    fmt=b'tree'

    def deserialize(self, data):
        self.items = gitUtil.tree_parse(data)

    def serialize(self):
        return gitUtil.tree_serialize(self)

    def init(self):
        self.items = list()

class GitTag(GitCommit):
    fmt = b'tag'

#This class represent a single entry of Index file.    
class GitIndexEntry(object):
    def __init__(self, ctime=None, mtime=None, dev=None, ino=None,
                 mode_type=None, mode_perms=None, uid=None, gid=None,
                 fsize=None, sha=None, flag_assume_valid=None,
                 flag_stage=None, name=None):
        # The last time a file's metadata changed.  This is a pair
        # (timestamp in seconds, nanoseconds)
        self.ctime = ctime
        # The last time a file's data changed.  This is a pair
        # (timestamp in seconds, nanoseconds)
        self.mtime = mtime
        # The ID of device containing this file
        self.dev = dev
        # The file's inode number
        self.ino = ino
        # The object type, either b1000 (regular), b1010 (symlink),
        # b1110 (gitlink).
        self.mode_type = mode_type
        # The object permissions, an integer.
        self.mode_perms = mode_perms
        # User ID of owner
        self.uid = uid
        # Group ID of ownner
        self.gid = gid
        # Size of this object, in bytes
        self.fsize = fsize
        # The object's SHA
        self.sha = sha
        self.flag_assume_valid = flag_assume_valid
        self.flag_stage = flag_stage
        # Name of the object (full path this time!)
        self.name = name

#Now on the detail of file index, it's made of three part:
#   _An header with the format version number and the number of entries the index holds.
#   _A series of entries, sorted, each representing a file; padded to multiple of 8 bytes.
#   _A series of optional extension which I'll ignore for the sake of simplicity.
class GitIndex(object):
    version = None
    entries = []
    def __init__(self, version = 2, entries = None):
        if not entries:
            entries = list()

        self.version = version
        self.entries = entries

#GitIgnore is a class that hold a list of absolute rule, a dict (hashmap) of relative rules.
#The key to this hashmap are dictionaries, relative to the root of a work tree.
class GitIgnore(object):
    absolute = None
    scoped = None
    def __init__(self, absolute, scoped):
        self.absolute = absolute
        self.scoped = scoped