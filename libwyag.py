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
    if   args.command == "add"          : cmd_add(args)
    elif args.command == "cat-file"     : cmd_cat_file(args)
    elif args.command == "check-ignore" : cmd_check_ignore(args)
    elif args.command == "checkout"     : cmd_checkout(args)
    elif args.command == "commit"       : cmd_commit(args)
    elif args.command == "hash-object"  : cmd_hash_object(args)
    elif args.command == "init"         : cmd_init(args)
    elif args.command == "log"          : cmd_log(args)
    elif args.command == "ls-files"     : cmd_ls_files(args)
    elif args.command == "ls-tree"      : cmd_ls_tree(args)
    elif args.command == "rev-parse"    : cmd_rev_parse(args)
    elif args.command == "rm"           : cmd_rm(args)
    elif args.command == "show-ref"     : cmd_show_ref(args)
    elif args.command == "status"       : cmd_status(args)
    elif args.command == "tag"          : cmd_tag(args)
    else                                : print("Bad command.")
            
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
        # to try to reproduce in this simplified version. Since the point of this simplified version is to learn and 
        #demonstrate Git, not to produce a working implementation, this limitation is acceptable.

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

#ls-file command displays the names of files in the staging area. This version of ls-file
#will be much simpler and added a --verbose option that doesn't exist in git in order to 
#display every single bit of info in the index file for testing and educational purpose.
def cmd_ls_files(args):
    repo = gitRepo.repo_find()
    index = gitUtil.index_read(repo)
    if args.verbose:
        print("Index file format v{}, containing {} entries.".format(index.version, len(index.entries)))
    
    for entry in index.entries:
        print(entry.name)
        if args.verbose:
            print("  {} with perms: {:o}".format(
                { 0b1000: "regular file",
                0b1010: "symlink",
                0b1110: "git link" }[entry.mode_type],
                entry.mode_perms))
            print("  on blob: {}".format(entry.sha))
            print("  created: {}.{}, modified: {}.{}".format(
                datetime.fromtimestamp(entry.ctime[0])
                , entry.ctime[1]
                , datetime.fromtimestamp(entry.mtime[0])
                , entry.mtime[1]))
            print("  device: {}, inode: {}".format(entry.dev, entry.ino))
            #print("  user: {} ({})  group: {} ({})".format(
            #    pwd.getpwuid(entry.uid).pw_name,
            #    entry.uid,
            #    grp.getgrgid(entry.gid).gr_name,
            #    entry.gid))
            print("  flags: stage={} assume_valid={}".format(
                entry.flag_stage,
                entry.flag_assume_valid))

#The check-ignore command takes a list of paths and output back those paths that should be ignored.
def cmd_check_ignore(args):
    repo = gitRepo.repo_find()
    rules = gitUtil.gitignore_read(repo)
    for path in args.path:
        if gitUtil.check_ignore(rules, path):
            print(path)

#status command is more complicated than ls-file command because it needs to compare the index
#with both HEAD and the actual filesystem. You call git status to know which files were added,
#removed, or modified since the last commit, and which of these changes are actually staged,
#and will make it to the next commit. So status command actually compare the HEAD with
#the staging area, and staging area with the work tree.

#I'll implement status command in three part:
#   _The active branch or "detached HEAD" 
#   _The difference between the index and the working tree ("Changes not stage for commit")
#   _The difference betweeen HEAD and the index ("Changes to be committed" and "Untracked files")

def cmd_status(_):
    repo = gitRepo.repo_find()
    index = gitUtil.index_read(repo)

    gitUtil.status_branch(repo)
    gitUtil.status_head_index(repo, index)
    print()
    gitUtil.status_index_worktree(repo, index)

#Now to commit, we need three last thing to create the actual commit:
#   _Commands to modify the index, so our commits arent's just a copy of their parent.
#    Those commands are 'add' and 'rm' commands.
#   _Those commands need to write the modified index back, since we commit from the index.
#   _And obviously, we'll need the commit function and it associated command
 
#The 'rm' command remove an entry from an index which mean that the next commit won't include this file.
def cmd_rm(args):
    repo = gitRepo.repo_find()
    gitUtil.rm(repo, args.path)

#The 'add' command consist of 4 step:
#   _Begin by removing existing index entry, if there's one, without removing the file itself (this is 
#    why the 'rm' function has those optional arguments).
#   _Then hash the file into a glob oject
#   _Create its entry
#   _Finally write the modified index back
def cmd_add(args):
    repo = gitRepo.repo_find()
    gitUtil.add(repo, args.path)

#After we've modified the index, so actually staged changes, the 'commit' command will turn
#those changes into a commit. 

#To do so, we first need to convert the index into a tree object, generate and store the corresponding 
#commit object, and update the HEAD branch to the new commit
