#!/bin/bash -e

cd `dirname $0`

source _repos.sh
ROOT=$(abspath `pwd`)
BASE=$(abspath $ROOT/..)

CLONE_ROOT="https://github.com/firstwiki"

if gem list -i github-pages > /dev/null; then
	echo "github-pages gem already installed"
else
	echo "Initializing ruby environment"
	gem install bundler
	bundle install
fi


cd ..

echo "Linking dev.sh"

# setup dev script
if [ ! -f dev.sh ]; then
	ln -s "$ROOT"/dev.sh dev.sh
fi

echo "Cloning git repositories"

for repo in $ALL_REPOS; do
	if [ ! -d $repo ]; then
		git clone $CLONE_ROOT/$repo
		pushd $repo
		git submodule init
		git submodule update
		popd
	fi
done

echo "Clones complete."

# Create _site directory that contains everything
if [ ! -d _site ]; then
	echo "Creating combined _site directory"

	mkdir _site

	for repo in $REPOS; do
		if [ "$repo" != "firstwiki.github.io" ]; then
			ln -s "$BASE"/$repo/_site _site/$repo
		fi
	done

	# special case.. TODO, make less special
	SPECIAL="common docs news search index.html 404.html"
	for s in $SPECIAL; do
		ln -s "$BASE"/firstwiki.github.io/_site/$s _site/$s
	done
fi

echo "Done."
