FIRSTwiki management scripts
============================

This is a repository of scripts useful for doing local development on
FIRSTwiki. Most users probably don't want to use these.. but you never
know.

Currently, local development using these scripts on Windows is not
supported. It'll probably work with msys2 or git for windows bash
environment, but I haven't tried it.

Setup (OSX/Linux)
=================

* Ensure that ruby is installed, you will probably want to use RVM.
  * See https://rvm.io/rvm/install for details

* Install the required ruby packages

	gem install bundler
	bundle install

* Create a directory for your wiki stuff

	mkdir wiki
	cd wiki

* Clone this scripts repository into it

	git clone https://github.com/firstwiki/_scripts

* Run './init_env.sh' to clone all repos and setup the environment

	cd _scripts
	./init_env.sh

Usage
=====

You can use ./dev.sh to do a lot of things on all of the repos at once! For example, to update all of your repos:

	./dev.sh pull

Or to build all sites:

	./dev.sh build

To serve an individual site locally, you can use jekyll to do this. Each repo has
'run_server.sh' script that will do this:

	cd wiki
	./run_server.sh

To serve all of the sites at the same time, then use this (requires all sites to
be built first!)

	./dev.sh serve_site

Modifying _common
-----------------

_common is a special repository that all of the repositories share, so it's
set up as a git submodule so that the code doesn't need to be copied to
each of them. However, that makes it annoying to do local development when
you want to change it and test on all of the repos. What you can do is use
symlinks so that each repository is working on the same directory -- and then
when it's time to commit, you can roll back to the submodule. The workflow
is something roughly like this.

Set up the symlinks:

	./dev.sh link

Make your changes to common, then do a commit there:

	cd _common
	git commit -a 
	cd ..

Restore the git submodules (required to commit)

	./dev.sh unlink

Updating _common across all repos
---------------------------------

**Note**: Normal users should not do this. Instead, fork/commit to _common,
and once your PR is accepted then an adminstrator will update all
repositories for you using these steps.

If you are a FIRSTwiki administrator (not a moderator), you can update
all repos with the latest version of _common by doing the following:

	./dev.sh unlink
	./dev.sh update



