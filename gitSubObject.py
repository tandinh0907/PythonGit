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