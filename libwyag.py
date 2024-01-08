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
import gitCommand
import Comparser


def main(argv=sys.argv[1:]):
    args = Comparser.argparser.parse_args(argv)
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
    gitCommand.cat_file(repo, args.object, fmt=args.type.encode())

def cmd_hash_object(args):
    if args.write:
        repo = gitRepo.repo_find()
    else:
        repo = None

    with open(args.path, "rb") as fd:
        sha = gitCommand.object_hash(fd, args.type.encode(), repo)
        print(sha)

def cmd_log(args):
    repo = gitRepo.repo_find()
    print("digraph wyaglog{")
    print("  node[shape=rect]")
    gitCommand.log_graphviz(repo, gitCommand.object_find(repo, args.commit), set())
    print("}")