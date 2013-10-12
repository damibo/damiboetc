"""
Copyright 2007 VMware, Inc.  All rights reserved. -- VMware Confidential

VMware Installer
"""
from vmis import PRODUCT_NAME, PRODUCT_SUFFIX

DEST = LIBDIR/'vmware-installer/2.1.0'
CLEANUP = CONFDIR/'.cleanup'

# The 1.0 Installer looks in very specific locations for existing installs
# (/etc/vmware and /etc/vmware-vix)
OLDCONFDIR = Destination('/etc/vmware')
OLDBOOTSTRAPS = ['/etc/vmware', '/etc/vmware-vix']

installerLinks = ['vmware-installer', 'vmware-uninstall',
                  'vmware-uninstall-vix']

class VMwareInstaller(Installer):

   def InitializeQuestions(self, old, new, upgrade):
      # Only ask questions if they are not already set.  Otherwise we
      # can potentially end up changing paths from their old values to
      # their new values before {Pre,Post}Uninstall runs which assumes
      # its old value.
      #
      # Perhaps in the future we can ask these questions
      # per-transaction and use the new values for new installs but
      # not upgrades?  This is tricky though because a new dependent
      # could have been introduced which assumes being installed
      # alongside other components but would end up getting new paths.
      def _addQuestion(questionType, key, text, default):
         defaultAnswer = self.GetAnswer(key)
         if not defaultAnswer:
            defaultAnswer = default
         self.AddQuestion(questionType, key=key, text=text, default=defaultAnswer,
                          required=True, mustExist=False, level='CUSTOM')

      _addQuestion('Directory', key='prefix',
                   text='System path prefix. Please note that choosing a path other '
                   'than /usr may result in missing icons, application launchers, and '
                   'other desktop integrations.', default=PREFIX)

      _addQuestion('Directory', 'libdir', text='System lib directory.', default=LIBDIR)

      _addQuestion('Directory', key='datadir', text='Architecture-independent files.',
                   default=DATADIR)

      _addQuestion('Directory', key='bindir', text='User level binaries.', default=BINDIR)

      _addQuestion('Directory', key='sbindir', text='Super user level binaries.',
                   default=SBINDIR)

      _addQuestion('Directory', key='docdir', text='Documentation.', default=DOCDIR)

      _addQuestion('Directory', key='mandir', text='Manual pages.', default=MANDIR)

      _addQuestion('Directory', key='includedir', text='Header files.', default=INCLUDEDIR)

      # XXX: Using non-default sysconfdir is not supported now. Comment out.
      #_addQuestion('Directory', key='sysconfdir', text='System configuration files.',
      #             default=SYSCONFDIR)

      # These have different defaults.
      if self.GetAnswer('initdir') is None:
         self.AddQuestion('InitDir', key='initdir', text='System service runlevel directory (contains rc?.d directories).  Use an empty directory if your system does not support rc?.d style directories.',
                          level='CUSTOM')

      if self.GetAnswer('initscriptdir') is None:
         self.AddQuestion('InitScriptDir', key='initscriptdir', text='System service scripts directory (commonly /etc/init.d).',
                          level='CUSTOM')

      self.AddQuestion('YesNo', key='installShortcuts', required=True,
                       text='Do you want to install shortcuts for your desktop?',
                       level='CUSTOM', default='yes')

   def PreTransactionUninstall(self, old, new, upgrade):
      keepConfig = ENV.get('VMWARE_KEEP_CONFIG')
      keepConfigStored = self.GetConfig('keepConfigOnUninstall')
      askQuestion = True
      if keepConfig:
         if keepConfig == 'no':
            self.SetConfig('keepConfigOnUninstall', 'no')
            askQuestion = False
         else:
            self.SetConfig('keepConfigOnUninstall', 'yes')
            askQuestion = False

      # Set a sane default if this has never been answered
      if not keepConfigStored:
         keepConfigStored = 'yes'

      # If the environment variable was set, there's no need to ask.  This also supports
      # silent uninstallation.
      if askQuestion:
         currentVersion = self.GetConfig('currentVersion')
         if currentVersion and \
            Version(currentVersion) == Version('2.1.0') and \
            not upgrade:
            # If this is the last installer, it's being uninstalled,
            # and we are not upgrading, then query the user if they
            # would like to keep their configuration files.
            self.AddQuestion('YesNo',
                             key='keepConfigOnUninstall',
                             text='All configuration information is about to be removed. ' \
                                  'Do you wish to keep your configuration files?',
                             required=False,
                             default=keepConfigStored,
                             level='REGULAR')

   def InitializeInstall(self, old, new, upgrade):
      bin = DEST/''
      bin.perm = BINARY

      self.AddTarget('File', 'vmis*', DEST)
      self.AddTarget('File', 'vmware/*', DEST/'vmware')
      self.AddTarget('File', 'vmware-installer*.py', DEST)
      self.AddTarget('File', 'init.sh', DEST/'init.sh')
      # We need to create extra bootstrap files for the 1.0 Installer with BINDIR set
      # correctly since the 1.0 .bundle installer needs it in order to hook into our
      # downgrade script.   Otherwise it will just install and stomp all over portions
      # of our files.
      self.AddTarget('File', 'vmware-installer', bin/'vmware-installer')
      self.AddTarget('File', 'vmware-uninstall-downgrade', bin/'vmware-uninstall-downgrade')

      self.AddTarget('File', 'artwork/*', DEST/'artwork')
      self.AddTarget('File', 'lib/*', DEST/'lib')
      self.AddTarget('File', 'sopython/*', DEST/'sopython')
      self.AddTarget('File', 'bin/*', DEST/'bin')

      # Python
      self.AddTarget('File', 'python/*', DEST/'python')
      self.SetPermission(DEST/'python/python', BINARY)
      self.SetPermission(DEST/'python/libpython.so', BINARY)
      self.SetPermission(DEST/'vmis-launcher', BINARY)
      self.SetPermission(DEST/'sopython/*', BINARY)

      self.SetPermission(DEST/'bin/*', BINARY)

   def PostInstall(self, old, new, upgrade):
      bin = DEST/''

      # Store installer information in the database
      self.SetConfig('%s.vmisloc' % '2.1.0', DEST)
      self.SetConfig('%s.pyloc'   % '2.1.0', DEST/'python')
      self.SetConfig('%s.pyver'   % '2.1.0', PYTHON_VERSION)

      # Set up installer specific files.  These are shared between installers, so
      # must be laid down carefully. We only want to set up files if there is
      # either no existing installer or we are the latest and greatest.
      systemVersion = self.GetConfig('currentVersion')
      if systemVersion is None or Version(systemVersion) <= Version(new):
         # Set ourselves as the current version of the installer to use
         self.SetConfig('currentVersion', '2.1.0')

         # Remove existing symlink to pave the way for the new one.
         try:
            (BINDIR/'vmware-installer').remove()
         except OSError:
            # We don't care if it already doesn't exist.
            pass
         # Create installer hooks.  symlink expects a string and can't convert
         # a ComponentDestination object.  Convert them manually.
         try:
            BINDIR.makedirs()
         except OSError:
            # It's okay if it already exists.
            pass
         path(bin/'vmware-installer').symlink(str(BINDIR/'vmware-installer'))

         # Create necessary bootstrap files
         self._WriteInstallerBootstrapFile(installerPresent=True)

         # The 1.0 installer looks for bootstrap in these locations
         # with a BINDIR in them.  We need to create them if they
         # don't already exist
         for bstrap in OLDBOOTSTRAPS:
            bootstrap = path(bstrap)/'bootstrap'
            if not bootstrap.exists():
               try:
                  path(bstrap).makedirs()
               except OSError:
                  pass
               bootstrap.write_bytes('BINDIR="%s"\n\n' % BINDIR, append=False)

      for i in DEST.walkfiles('*.py'):
         compiled = self.CompilePythonFile(i)
         self.RegisterFile(compiled)

      # Configure Gtk+.
      # @todo: make it its own component
      libconf = DEST/'lib/libconf'
      replace = ('etc/pango/pangorc', 'etc/pango/pango.modules', 'etc/pango/pangox.aliases',
                 'etc/gtk-2.0/gdk-pixbuf.loaders', 'etc/gtk-2.0/gtk.immodules')
      replace = [libconf/r for r in replace]
      templates = ['@@LIBCONF_DIR@@']

      # LIBCONF_DIR may have already been replaced by the bootstrapper
      # so that we can run.  If so, it set a key pointing to what it
      # set the libconf dir to where it is in /tmp which we must
      # change to the installed location.
      tmpLibconf = self.GetConfig('libconf')
      tmpLibconf and templates.append(tmpLibconf)

      for i in replace:
         # @todo: would be useful to have our own internal sed
         for template in templates:
            self.RunCommand('sed', '-e', 's,%s,%s,g' % (template, libconf), '-i', i)

      self.DelConfig('libconf')

   def _WriteInstallerBootstrapFile(self, installerPresent=True):
      # To mitigate a bug in the older installers, which would attempt to run
      # the (now uninstalled, and thus missing), newer installer and crash, we need
      # to re-write the bootstrap file so that VERSION="0.1", which will always
      # force an older installer to use itself rather than trying to chain the the
      # "newer", non-existant installer
      if installerPresent:
         legacyVersionStamp = '2.1.0'
      else:
         legacyVersionStamp = '0.1'

      bootstrap = CONFDIR/'bootstrap'
      bootstrap.write_bytes('VMWARE_INSTALLER="%s"\n\n' % DEST, append=False)
      bootstrap.write_bytes('VERSION="%s" # For backwards compatibility\n' % legacyVersionStamp, append=True)
      bootstrap.write_bytes('VMISVERSION="%s"\n' % '2.1.0', append=True)
      bootstrap.write_bytes('VMISBUILDNUM="%s"\n' % '1278091', append=True)
      bootstrap.write_bytes('VMISPYVERSION="%s"\n' % PYTHON_VERSION, append=True)


   def PostTransactionInstall(self, old, new, upgrade):
      # The .cleanup file is originally created when loading the
      # database when the database doesn't already exist.  Now that
      # the transaction for vmware-installer has been committed we can
      # remove this file as the installer framework has been
      # installed and configured.
      # However, if the database already existed, this file will not be
      # created and the remove would fail.  No need to remove it, hence
      # the try/except.
      try:
         CLEANUP.remove()
      except OSError:
         log.Debug('%s did not exist.' % CLEANUP)

   def PreUninstall(self, old, new, upgrade):
      # Remove vmware-installer keys
      self.DelConfig('%s.vmisloc' % '2.1.0')
      self.DelConfig('%s.pyloc'   % '2.1.0')
      self.DelConfig('%s.pyver'   % '2.1.0')

   def PostUninstall(self, old, new, upgrade):
      currentVersion = self.GetConfig('currentVersion')
      keepConfig = self.GetConfig('keepConfigOnUninstall')
      # currentVersion should not be able to be None under normal install and
      # uninstall, but in a rollback scenario it can happen.
      if currentVersion and Version(currentVersion) == Version('2.1.0'):
         if keepConfig != 'yes':
            # If we are the newest installer, it means we're the last to go.
            # Clean up after ourselves.

            # Remove bootstrap files and set database .cleanup file
            bstraps = OLDBOOTSTRAPS + [CONFDIR]
            # Check if the old VIX or Player/WS is installed.  If so,
            # don't clean up the bootstrap files.
            for suffix in ['', '-vix']:
               oldfile = path('/etc/vmware%s/bootstrap' % suffix)
               if oldfile.exists():
                  text = oldfile.bytes()
                  if text.find('VERSION="1.0"') != -1:
                     bstraps.remove('/etc/vmware%s' % suffix)

            # Now cleanup our bootstraps
            if not upgrade:
               for bstrap in bstraps:
                  try:
                     bootstrapDir = path(bstrap)
                     bootstrap = bootstrapDir/'bootstrap'
                     bootstrap.unlink(ignore_errors=True)
                     bootstrapDir.rmdir()
                  except OSError, e:
                     log.Info('Problem removing bootstrap file %s: %s' % (bootstrap, e))
               # Signal cleanup of database.  This is done in PreUninstall
            # because if the uninstall only partially completes the
            # installer is in an inconsistent state and may not be able to
            # remove itself.
            CLEANUP.touch()

            # Remove installer symlink
            try:
               (BINDIR/'vmware-installer').remove()
            except OSError:
               # We don't care if it already doesn't exist.
               pass

            # Clear our config key
            self.DelConfig('currentVersion')

            # XXX: SYSCONFDIR/'config' - This file is used by VIX, Player, and
            # WS, so should only be uninstalled when one of those is the last to
            # go.  For now, it's going to go here, so it's removed from the system
            # when everything else goes.  A better solution should be found that
            # involves the VIX, Player, and WS component files.  It doesn't belong
            # in this one.
            # Only do this if we are not upgrading.
            if not upgrade:
               # If we are on an ESX system, we do *NOT* want to remove /etc/vmware/config
               # since ESX needs it!
               if not path('/proc/vmware/version').exists():
                  try:
                     (SYSCONFDIR/'vmware/config').remove()
                  except OSError, e:
                     log.Info('Error removing file: %s.' % (SYSCONFDIR/'vmware/config'))
                     log.Info(e)
                  # And finally, remove SYSCONFDIR/vmware
                  try:
                     (SYSCONFDIR/'vmware').rmdir()
                  except OSError, e:
                     log.Info('Error removing directory: %s.' % (SYSCONFDIR/'vmware'))
                     log.Info(e)
         else:
            # The user chose to keep their configuration, but we still need to remove the
            # currentVersion key since there is no current version of the installer installed
            # anymore
            self.DelConfig('currentVersion')

            # Re-write the bootstrap file
            self._WriteInstallerBootstrapFile(installerPresent=False)
