Changelog
=========
This is a log of the latest changes and improvements to KLibs.

0.7.5a10
--------

Released on XXXX-XX-XX.

Fixed Bugs:

* Fixed a bug in :class:`~klibs.KLJSON_Object.JSON_Object` where importing a
  JSON file with a key less than 3 characters would raise an exception.
* Fixed a bug that prevented :func:`~klibs.KLUserInterface.key_pressed` from
  reliably catching quit events.
