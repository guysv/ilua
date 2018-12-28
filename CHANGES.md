## [0.2.0] - UNRELEASED
- Feature: History - ILua now remembers your executed code.
- Tweak: Kernel application environment variable prefix is now inferred from kernel implementation field
- Tweak: TXKernel is now merged into ILua
- Tweak: Add pywin32 as an explicit dependency
- Bugfix: Set the right content-type for lua code (Thanks to @dennii)
- Bugfix: Fix crash from encoding errors on unicode output
- Bugfix: tweaked kernel's language_info to contain Lua's version
## [0.1.0] - 2018-11-06
- Initial release