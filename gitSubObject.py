import gitCommand

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
        self.kvlm = gitCommand.kvlm_parse(data)

    def serialize(self):
        return gitCommand.kvlm_serialize(self.kvlm)
    
class GitTreeLeaf (object):
    def __init__(self, mode, path, obj):
        self.mode = mode
        self.path = path
        self.obj = obj

class GitTree(GitObject):
    fmt=b'tree'

    def deserialize(self, data):
        self.items = gitCommand.tree_parse(data)

    def serialize(self):
        return gitCommand.tree_serialize(self)

    def init(self):
        self.items = list()