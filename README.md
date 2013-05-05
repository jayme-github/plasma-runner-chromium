# Chromium runner

Launch [chromium](http://www.chromium.org/) bookmarks and keywords via [krunner](http://userbase.kde.org/Plasma/Krunner).

With KDE 4.10 it looks like the included bookmarks runner can access chrome/chromium bookmarks, see: https://git.reviewboard.kde.org/r/105673/
But ther is still need for a cool way to sync chrome/chromium keywords and KDE web-shortcuts.

## Installation

### Requirements
- [PyKDE4](http://techbase.kde.org/Development/Languages/Python)

Easily installed, for example, via Ubuntu's package management system like so:

```bash
sudo apt-get install python3-pykde4
```

### Once you have what you need
- Clone this repository

  ```bash
  git clone https://github.com/jayme-github/chromium-runner.git
  ```
  
- Use the provided installer

  ```bash
  . install.sh
  ```
