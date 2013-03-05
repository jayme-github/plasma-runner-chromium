import os, sqlite3, json
from shutil import copy2
from tempfile import mkstemp
from urlparse import urljoin
from urllib import urlencode
from PyQt4.QtCore import SIGNAL
from PyKDE4 import plasmascript
from PyKDE4.plasma import Plasma
from PyKDE4.kdeui import KIcon
from PyKDE4.kdecore import KToolInvocation
from PyKDE4.kio import KDirWatch

class ChromiumRunner(plasmascript.Runner):

    DEFAULT_GOOGLE_URL = "https://www.google.com/"
    
    def init(self):
        self._keywords = {}
        self._bookmarks = []
        self._googleBaseURL = ChromiumRunner.DEFAULT_GOOGLE_URL

        # FIXME: Should go to config
        homePath = os.environ.get("HOME")
        self._pathWebData    = os.path.join(homePath, ".config/chromium/Default/Web Data")
        self._pathLocalState = os.path.join(homePath, ".config/chromium/Local State")
        self._pathBookmarks  = os.path.join(homePath, ".config/chromium/Default/Bookmarks")

        self.setSyntaxes([
            Plasma.RunnerSyntax(
                "<Chromium keyword> :q:",
                "Search for :q: using Chromium keyword"),
            Plasma.RunnerSyntax(
                ":q:",
                "Search for :q: in your Chromium bookmarks")
        ])

        # Initially read data
        self._readKeywords()
        self._readBookmarks()
        self._readLastKnownGoogleUrl()

        # Watch the files for changes
        self._watcher = KDirWatch(self)
        self._watcher.addFile(self._pathWebData)
        self._watcher.addFile(self._pathLocalState)
        self._watcher.addFile(self._pathBookmarks)
        self.connect(self._watcher, SIGNAL("created(QString)"), self._updateData)
        self.connect(self._watcher, SIGNAL("dirty(QString)"), self._updateData)

    def _updateData(self, path):
        """
        Called by KDirWatch if a watched dir has changed (dirty).
        """
        if path == self._pathWebData:
            self._readKeywords()
        elif path == self._pathLocalState:
            self._readLastKnownGoogleUrl()
        elif path == self._pathBookmarks:
            self._readBookmarks()

    def _readKeywords(self):
        """
        Read chromium keywords.
        """
        # Copy Chromium Web Data as it is locked if Chromium running... This is
        # risky as sqlite could be in the middle of performing some transaction!
        if os.path.isfile(self._pathWebData) and os.access(self._pathWebData, os.R_OK):
            _, dbfile = mkstemp("krunner-chromium")
            copy2(self._pathWebData, dbfile)
            cur = sqlite3.connect(dbfile).cursor()
            try:
                cur.execute("SELECT short_name, keyword, url FROM keywords")
                self._keywords = {}
                for shortName, keyword, url in cur.fetchall():
                    if not keyword in self._keywords:
                        self._keywords[keyword] = (shortName, url) # order matters
            finally:
                cur.close()
                os.unlink(dbfile)

    def _readBookmarks(self):
        """
        Read Chromium bookmarks.
        """
        with open(self._pathBookmarks, 'r') as bfile:
            def walk(element):
                for item in element:
                    if item["type"] == "url":
                        tmp = { "url": item["url"], "name": item["name"] }
                        if not tmp in self._bookmarks:
                            self._bookmarks.append(tmp)
                    elif item["type"] == "folder":
                        walk(item["children"])
            self._bookmarks = []
            jsonRoots = json.load(bfile).get("roots", {})
            for key in (v for v in jsonRoots.itervalues() if type(v) is dict):
                walk(key.get("children", {}))

    def _readLastKnownGoogleUrl(self):
        """
        Read the last_known_google_url from `Local State`.
        """
        with open(self._pathLocalState, 'r') as localStateFile:
            self._googleBaseURL = json.load(localStateFile)\
                .get("browser", {})\
                .get("last_known_google_url", ChromiumRunner.DEFAULT_GOOGLE_URL)

    def match(self, context):
        """
        Inspect the current query and provide appropriate matches.
        """
        if not context.isValid() or not self._keywords or not self._bookmarks:
            return

        query = context.query().trimmed()

        # look for keywords
        for keyword in self._keywords:
            if query.startsWith(keyword + " "):
                searchTerm = query[len(keyword)+1:]
                if len(searchTerm) >= 2:
                    self._matchKeyword(context, query, searchTerm, keyword)

        # look for bookmarks
        def queryInBookmarks(element):
            if query.toLower() in element["name"].lower():
                return element
        for bookmark in filter(queryInBookmarks, self._bookmarks):
            self._matchBookmark(context, query, bookmark)

    def _matchBookmark(self, context, query, matchedBookmark):
        url, name = matchedBookmark["url"], matchedBookmark["name"]
        m = Plasma.QueryMatch(self.runner)
        m.setText("\"%s\"\n%s" % (name, url))
        m.setType(Plasma.QueryMatch.ExactMatch)
        m.setIcon(KIcon("bookmarks"))
        m.setData(url)
        context.addMatch(query, m)

    def _matchKeyword(self, context, query, searchTerm, matchedKeyword):
        shortName, url = self._keywords[matchedKeyword]

        url = url.replace("{searchTerms}", searchTerm)

        # Default google search URL is some freaky contruction like:
        # {google:baseURL}search?{google:RLZ}{google:acceptedSuggestion}{google:originalQueryForSuggestion}{google:searchFieldtrialParameter}{google:instantFieldTrialGroupParameter}sourceid=chrome&client=ubuntu&channel=cs&ie={inputEncoding}&q=%s
        # google:baseURL is in attr "last_known_google_url" in ~./config/chromium/Local State
        # Quick workaround...
        if url.startswith("{google:baseURL}"):
            url = urljoin(self._googleBaseURL,
                          "search?" + urlencode({"q": query, "aq": "f"}))

        m = Plasma.QueryMatch(self.runner)
        m.setText("Query \"%s\" for '%s'\n%s" % (shortName, searchTerm, url))
        m.setType(Plasma.QueryMatch.ExactMatch)
        m.setIcon(KIcon("chromium-browser"))
        m.setData(url)
        context.addMatch(query, m)

    def run(self, context, match):
        if context.isValid():
            KToolInvocation.invokeBrowser(match.data().toString())


def CreateRunner(parent):
    return ChromiumRunner(parent)
