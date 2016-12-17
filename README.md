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

First, ensure that ruby is installed, you will probably want to use RVM (See
https://rvm.io/rvm/install for details).

Install the required ruby packages

	gem install bundler
	bundle install

Create a directory for your wiki stuff

	mkdir wiki
	cd wiki

Clone this scripts repository into it

	git clone https://github.com/firstwiki/_scripts

Run './init_env.sh' to clone all repos and setup the environment

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

If you wish jekyll to watch the files and autoregenerate them when serving the
site, this will launch all of the sites and watch them:

	./dev.sh serve_site --watch

Modifying _common
-----------------

`_common` is a special repository that all of the repositories share, so it's
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

Running the server without admin privlidges
-------------------------------------------

**Note**: These instructions were developed on mac, and instructions may differ on other platforms

Without admin rights, you cannot add new gems (such as Bundler) to the Ruby installation. If you already have bundler installed on your system, you can go ahead and skip this. If you don't, you'll need to install [RVM](https://rvm.io) (Ruby Version Manager). You can do so simply using the two commands:

	gpg --keyserver hkp://keys.gnupg.net --recv-keys 409B6B1796C275462A1703113804BB82D39DC0E3
	\curl -sSL https://get.rvm.io | bash -s stable

You'll need to install `gpg` if you don't have it installed already. The first command adds the public key for the install server, and the second actually downloads and runs the install script. Double check RVM was installed by running the following command after opening a new terminal session:

	type rvm | head -1
	
If you get `rvm is a function`, RVM was successfully installed. RVM, by default, does not actually have any copy of Ruby installed, so you'll need to install it:

	rvm install ruby-head
	
This will install the latest stable version of ruby (in this case 2.2.4, it'll output the vesion when installing it). It'll go ahead and install ruby and the required gems. Next, you'll need to make sure you're using the RVM ruby and not the system ruby, as we don't have access to edit the system ruby. Run the following command to see which ruby you are running:

	which ruby
	
If you get `.rvm` somewhere in the path, you are using the RVM ruby. If it says you are using the system ruby, run the following command to switch to the rvm ruby you just installed:

	rvm use 2.2.4
	
From here, you can now install `bundler` and follow the instructions listed at the top of this document. I created my own shell script and added the following at the top of it to make sure it loaded the correct ruby: (I installed 2.3.0 instead of 2.2.4)

	source ~/.rvm/scripts/rvm
	rvm use 2.3.0

"GitHub Metadata: No GitHub API authentication could be found" Error
===========================================================================
If you are editing locally, and when you save a file, it does not get updated on the local server, this may be the issue. Look at your console and see if you are getting this error:

	Regenerating: 1 file(s) changed at 2016-09-13 13:10:58    GitHub Metadata: No GitHub API authentication could be found. Some fields may be missing or have incorrect data.
	...error:
   	Error: SSL_connect returned=1 errno=0 state=SSLv3 read server certificate B: certificate verify failed
    	Error: Run jekyll build --trace for more information.
	
This is a known problem and can be solved by following these steps:

1. Create a personal access token in GitHub. This takes just a second, see [GitHub’s documentation](https://help.github.com/articles/creating-an-access-token-for-command-line-use/). When picking the scope(s) that you want to grant to the token, just select the `repo` checkbox.
2. Add a new system environment variable on your machine named `JEKYLL_GITHUB_TOKEN` and set the value equal to the personal access token you generated.
3. [Go here](https://curl.haxx.se/ca/cacert.pem), copy all the text in the page, and save it as a file named cacert.pem somewhere on your local machine.
4. Add a new system environment variable on your machine named `SSL_CERT_FILE` and set the value equal to the full file path of where you saved the `cacert.pem` file.
5. RESTART YOUR MACHINE (this is not optional)

Instructions courtest of [here](http://knightcodes.com/miscellaneous/2016/09/13/fix-github-metadata-error.html). Further instructions and a instruction video can be found there.
