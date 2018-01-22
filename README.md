# git-rsync

This utility help managing repo files between hosts with rsync.
* Save time typing commands
* Use <del>powerful</del> pathspec expression instead of `--include`/`--exclude`

## Install / Uninstall
In the project root, run `pip3 install .` or `pip3 uninstall gitrsync`

## Usage
### Add / Remove a remote host
`git rsync add examplehost example.com:myproject` <br>
`git rsync remove examplehost`

### List remote hosts
`git rsync list`

### Download / Upload files
`git rsync upload examplehost README.md` <br>
`git rsync download examplehost -- *.py`

### Advanced
See `git rsync --help`

