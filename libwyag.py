import argparse
import collections
import configparser
from datetime import datetime
#import grp, pwd
from fnmatch import fnmatch
import hashlib
from math import ceil
import os
import re
import sys
import zlib
import gitRepo
import gitUtil
import comParser


def main(argv=sys.argv[1:]):
    args = comParser.argparser.parse_args(argv)
    if   args.command == "add"         : cmd_add(args)
    elif args.command == "cat-file"    : cmd_cat_file(args)
    elif args.command == "checkout"    : cmd_checkout(args)
    elif args.command == "commit"      : cmd_commit(args)
    elif args.command == "hash-object" : cmd_hash_object(args)
    elif args.command == "init"        : cmd_init(args)
    elif args.command == "log"         : cmd_log(args)
    elif args.command == "ls-tree"     : cmd_ls_tree(args)
    elif args.command == "merge"       : cmd_merge(args)
    elif args.command == "rebase"      : cmd_rebase(args)
    elif args.command == "rev-parse"   : cmd_rev_parse(args)
    elif args.command == "rm"          : cmd_rm(args)
    elif args.command == "show-ref"    : cmd_show-ref(args)
    elif args.command == "tag"         : cmd_tag(tag)
            
def cmd_init(args):
    gitRepo.repo_create(args.path)

def cmd_cat_file(args):
    repo = gitRepo.repo_find()
    gitUtil.cat_file(repo, args.object, fmt=args.type.encode())

def cmd_hash_object(args):
    if args.write:
        repo = gitRepo.repo_find()
    else:
        repo = None

    with open(args.path, "rb") as fd:
        sha = gitUtil.object_hash(fd, args.type.encode(), repo)
        print(sha)

def cmd_log(args):
    repo = gitRepo.repo_find()
    print("digraph wyaglog{")
    print("  node[shape=rect]")
    gitUtil.log_graphviz(repo, gitUtil.object_find(repo, args.commit), set())
    print("}")

def cmd_ls_tree(args):
    repo = gitRepo.repo_find()
    gitUtil.ls_tree(repo, args.tree, args.recursive)


    #This is a oversimplified version of the actual "git checkout" command.
    #This version of check out will work:
        #_It will take two arguments: a commit, and a directory. Git checkout only needs a commit.
        #_It will then instantiate the tree in the directory, if and only if the directory is empty.
        # Git is full of safeguards to avoid deleting data, which would be too complicated and unsafe 
        # to try to reproduce in this simplified version. Since the point of this simplified version is to learn and demonstrate git,
        # not to produce a working implementation, this limitation is acceptable.

def cmd_checkout(args):
    repo = gitRepo.repo_find()

    obj = gitUtil.object_read(repo, gitUtil.object_find(repo, args.commit))

    # If the object is a commit, we grab its tree
    if obj.fmt == b'commit':
        obj = gitUtil.object_read(repo, obj.kvlm[b'tree'].decode("ascii"))

    # Verify that path is an empty directory
    if os.path.exists(args.path):
        if not os.path.isdir(args.path):
            raise Exception("Not a directory {0}!".format(args.path))
        if os.listdir(args.path):
            raise Exception("Not empty {0}!".format(args.path))
    else:
        os.makedirs(args.path)

    gitUtil.tree_checkout(repo, obj, os.path.realpath(args.path))

def cmd_show_ref(args):
    repo = gitUtil.repo_find()
    refs = gitRepo.ref_list(repo)
    gitUtil.show_ref(repo, refs, prefix="refs")

def cmd_tag(args):
    repo = gitUtil.repo_find()

    if args.name:
        gitUtil.tag_create(repo,
                   args.name,
                   args.object,
                   type="object" if args.create_tag_object else "ref")
    else:
        refs = gitUtil.ref_list(repo)
        gitUtil.show_ref(repo, refs["tags"], with_hash=False)

def cmd_rev_parse(args):
    if args.type:
        fmt = args.type.encode()
    else:
        fmt = None
    repo = gitRepo.repo_find()
    print(gitUtil.object_find(repo, args.name, fmt, follow=True))