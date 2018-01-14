ifdef prefix
gitexecdir ?= $(prefix)/libexec/git-core
else
prefix ?= /usr/local
# Install to the libexec of git or git can't find it
gitexecdir ?= $(shell git --exec-path)
endif

INSTALL ?= install
RM ?= rm -f

GIT_RSYNC := git-rsync
GIT_RSYNC_PY := git-rsync.py

all: install

$(GIT_RSYNC): $(GIT_RSYNC_PY)
	cp $< $@
	chmod a+x $@

install: $(GIT_RSYNC)
	$(INSTALL) -d -m 755 $(DESTDIR)$(gitexecdir)
	$(INSTALL) -m 755 $(GIT_RSYNC) $(DESTDIR)$(gitexecdir)

uninstall:
	$(RM) $(DESTDIR)$(gitexecdir)/$(GIT_RSYNC)
