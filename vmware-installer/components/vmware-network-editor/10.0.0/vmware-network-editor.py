"""
Copyright 2010 VMware, Inc.  All rights reserved. -- VMware Confidential

VMware Network Editor component installer.
"""

DEST = LIBDIR/'vmware'

class NetworkEditor(Installer):
   """
   This class contains the installer logic for the NetworkEditor component.
   """

   def InitializeInstall(self, old, new, upgrade):
      self.AddTarget('File', 'bin/*', BINDIR)
      self.AddTarget('File', 'lib/*', DEST/'lib')
      self.SetPermission(BINDIR/'*', BINARY)

      # Symlink to AppLoader.
      self.AddTarget('Link', DEST/'bin/appLoader', DEST/'bin/vmware-netcfg')
