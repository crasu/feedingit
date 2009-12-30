import sys
from PyQt4 import QtGui
from PyQt4 import QtCore
from PyQt4.QtWebKit import QWebView
import feedparser
from QtGui import SIGNAL

class Feed:
    def __init__(self, url):
        self.feed=feedparser.parse(url)
    
    def getTitles(self):
        return self.feed["entries"]
    
    def getItem(self, index):
        return self.feed["entries"][index]
    
    def getArticle(self,index):
        entry = self.feed["entries"][index]
        #text = "<h4><a href=\"" + entry["link"] + "\">" + entry["title"] + "</a></h4>"
        text = "<small>" + entry["title"] + "</small>"
        text = text + "<BR />"
        text = text + entry["summary"]
        return text    
    
class Listing:
    listOfFeeds = ["http://rss.slashdot.org/Slashdot/slashdot",]
    
    def downloadFeeds(self):
        self.feeds = []
        for item in self.listOfFeeds:
            self.feeds.append(Feed(item))
            
    def getFeed(self, index):
        return self.feeds[index]
    
    def getListOfFeeds(self):
        return self.listOfFeeds


class ArticleDisplay(QtGui.QMainWindow):
    def __init__(self, parent, feed, index):
        QtGui.QMainWindow.__init__(self, parent)
        #self.setWindowTitle('Feeding It')
        
        text = feed.getArticle(index)
        web = QWebView()
        web.set_html(text)
        web.show()
        
        self.show()
  
class ListingDisplay(QtGui.QMainWindow):  
    def __init__(self, parent, feed):
        QtGui.QMainWindow.__init__(self, parent)
        
        listWidget = QtGui.QListWidget(self)
        index = 0
        for item in feed.getTitles():
            QtGui.QListWidgetItem(item["title"], listWidget)

            #button.connect("clicked", self.button_clicked, self, self.window, currentfeed, index)
            index=index+1
        
        #self.add(listWidget)
        self.show()

class FeedingIt(QtGui.QMainWindow):    
 
    def __init__(self, parent=None):
        QtGui.QMainWindow.__init__(self, parent)
        self.setWindowTitle('Feeding It')

        exit = QtGui.QAction(None, 'Exit', self)
        exit.setStatusTip('Exit application')
        self.connect(exit, QtCore.SIGNAL('triggered()'), QtCore.SLOT('close()'))

        self.mainWidget=QtGui.QWidget(self) # dummy widget to contain the
                                      # layout manager
        self.setCentralWidget(self.mainWidget)
        self.mainLayout=QtGui.QVBoxLayout(self.mainWidget)

        # Create MenuBar
        exitAction = QtGui.QAction('Exit', self)
        self.connect(exitAction, QtCore.SIGNAL('triggered()'), self.close)
        menubar = self.menuBar()
        file = menubar.addAction(exitAction)
        
        self.listing=Listing()
        self.displayListing() 
        
        #listOfFeeds = QtGui.QListWidget(self.mainWidget)
        
        #tmp = ["test","test1", "test2"]
        #for item in self.listing.getListOfFeeds():
        #for item in tmp:
        #    QtGui.QListWidgetItem(item, listOfFeeds)
        
        #layout = QtGui.QVBoxLayout()
        #layout.addWidget(listOfFeeds) 
        #self.setLayout(layout)
 
    def displayListing(self):
        #try:
        #    self.window.remove(self.pannableListing)
        #except:
        #    pass
        #self.vboxListing = gtk.VBox(False,10)
        #self.pannableListing = hildon.PannableArea()
        #self.pannableListing.add_with_viewport(self.vboxListing)

        for key in self.listing.getListOfFeeds():
            # Create the button for the feed
	    button = QtGui.QPushButton(self.listing.getFeedTitle(key), self)
	    button.setObjectName(key)
	    self.connect(button, SIGNAL("clicked()"), self.buttonFeedClicked)

            #button = gtk.Button(item)
            #button = hildon.Button(gtk.HILDON_SIZE_AUTO_WIDTH | gtk.HILDON_SIZE_FINGER_HEIGHT,
            #                  hildon.BUTTON_ARRANGEMENT_VERTICAL)
            #button.set_text(self.listing.getFeedTitle(key), self.listing.getFeedUpdateTime(key))
            #button.set_alignment(0,0,1,1)
            #button.connect("clicked", self.buttonFeedClicked, self, self.window, key)
            #self.vboxListing.pack_start(button, expand=False)
            pass
        #self.window.add(self.pannableListing)
        #self.window.show_all()
        
    def buttonFeedClicked(self):
	key = self.sender().objectName()
        self.displayFeed(key)
        
if __name__ == '__main__': 

    # Checking the configuration directory does exist
    if not isdir(CONFIGDIR):
        try:
            mkdir(CONFIGDIR)
        except:
            print "Error: Can't create configuration directory"
            sys.exit(1)
 
    #Creating Qt application
    app = QtGui.QApplication(sys.argv)
 
    feedingIt = FeedingIt()
    feedingIt.show()
 
    #Starting the application's main loop
    sys.exit(app.exec_())