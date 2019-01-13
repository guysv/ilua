## [0.2.1] - 2019-01-13
- Tweak: Optimized imports across entire project
- Bugfix: Removed an unused import that caused jupyter to crash python on windows
- Bugfix: Fix multiline statements to work for Lua 5.1
## [0.2.0] - 2019-01-12
- Feature: History - ILua now remembers your executed code.
- Tweak: Kernel application environment variable prefix is now inferred from kernel implementation field
- Tweak: TXKernel is now merged into ILua
- Tweak: Add pywin32 as an explicit dependency
- Tweak: Add pygments as an explicit dependency
- Bugfix: Fix crash on non-string error
- Bugfix: Set the right content-type for lua code (Thanks to @dennii)
- Bugfix: Fix crash from encoding errors on unicode output
- Bugfix: tweaked kernel's language_info to contain Lua's version
## [0.1.0] - 2018-11-06
- Initial release
