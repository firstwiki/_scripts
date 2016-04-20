#!/bin/bash -e
#
# Script for managing the _common directory. It's easier to do development if
# using symlinks.

ROOT=`dirname $0`
source $ROOT/_repos.sh
BASE=$(abspath $ROOT/..)

cd "$BASE"

if [ "$1" == "link" ]; then
    
    
    for repo in $REPOS; do 
        pushd $repo
        
        if [ ! -L _common ]; then
            
            # ensure that there aren't any changes.. 
            if [ -d _common ]; then 
                if ! git diff --exit-code --quiet _common; then
                    echo "Error: $repo/_common has uncommitted changes"
                    cd _common
                    git status
                    exit 1
                fi
            fi
            
            rm -rf _common
            ln -s "$BASE"/_common _common
        fi
        
        popd
    done
    
elif [ "$1" == "pull" ]; then
    
    for repo in $REPOS; do
        pushd $repo
        git pull
        popd
    done
    
elif [ "$1" == "push" ]; then
    
    for repo in $REPOS; do
        pushd $repo
        git push
        popd
    done
    
elif [ "$1" == "unlink" ]; then
    
    for repo in $REPOS; do 
        pushd $repo
        
        if [ -h _common ]; then
            rm _common
            git submodule update
        fi
        
        popd
    done
    
elif [ "$1" == "update" ]; then

    for repo in $REPOS; do 
        pushd $repo
        
        if [ -L _common ] || [ ! -d _common ]; then
            echo "Error: $repo/_common is not a real directory"
            exit 1
        fi
        
        pushd _common
        git pull origin master
        popd
        
        if ! git diff --exit-code --quiet _common; then
            git commit _common -m "Update _common"
        fi
        
        popd
    done

elif [ "$1" == "cmd" ]; then
    shift
    for repo in $REPOS; do
        pushd $repo
        "$@"
        popd
    done
else
    echo "Usage: $0 [cmd | link | pull | push | unlink | update]"
fi
