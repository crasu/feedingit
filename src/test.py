import sys
from PyQt4 import QtGui
from PyQt4 import QtCore
from PyQt4.QtWebKit import QWebView
import feedparser
import rss
from rss import *

from os.path import isfile, isdir
from os import mkdir

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

class FeedDisplay(QtGui.QMainWindow):
    def __init__(self, feed, title, parent=None):
        self.feed = feed
        self.title = title
        QtGui.QMainWindow.__init__(self, parent)
        self.setWindowTitle(self.title)
        
        self.mainWidget=QtGui.QWidget(self) # dummy widget to contain the
                                      # layout manager
        self.setCentralWidget(self.mainWidget)
        self.mainLayout=QtGui.QVBoxLayout(self.mainWidget)
        self.mainLayout.setSizeConstraint(1)
        self.displayFeed()
        print self.mainLayout.resizeMode
        self.show()
        
    def displayFeed(self):
        index = 0
        for item in self.feed.getEntries():
            button = QtGui.QPushButton(item["title"], self)
            button.setObjectName(str(index))
            self.mainLayout.addWidget(button)
            button.setFixedHeight(button.sizeHint().height())
            self.connect(button, QtCore.SIGNAL("clicked()"), self.buttonArticleClicked)           
            index = index + 1
        self.setFixedHeight(self.sizeHint().height())
            
    def buttonArticleClicked(self):
        index = int(self.sender().objectName())
        

class FeedingIt(QtGui.QMainWindow):    
 
    def __init__(self, parent=None):
        QtGui.QMainWindow.__init__(self, parent)
        self.setWindowTitle('Feeding It')

        exit = QtGui.QAction('Exit', self)
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
        for key in self.listing.getListOfFeeds():
            # Create the button for the feed
            button = QtGui.QPushButton(self.listing.getFeedTitle(key), self)
            button.setObjectName(key)
            self.mainLayout.addWidget(button)
            self.connect(button, QtCore.SIGNAL("clicked()"), self.buttonFeedClicked)
            
            
    def displayFeed(self, qtKey):
        key = str(qtKey)
        self.feedDisplay = FeedDisplay(self.listing.getFeed(key), self.listing.getFeedTitle(key), self)
        # Initialize the feed panel
        #self.vboxFeed = gtk.VBox(False, 10)
        #self.pannableFeed = hildon.PannableArea()
        #self.pannableFeed.add_with_viewport(self.vboxFeed)
        
        #index = 0
        #for item in self.listing.getFeed(key).getEntries():
            
            #button = hildon.Button(gtk.HILDON_SIZE_AUTO_WIDTH | gtk.HILDON_SIZE_FINGER_HEIGHT,
            #                  hildon.BUTTON_ARRANGEMENT_HORIZONTAL)
            #button.set_text(item["title"], time.strftime("%a, %d %b %Y %H:%M:%S",item["updated_parsed"]))
            #button.set_text(item["title"], time.asctime(item["updated_parsed"]))
            #button.set_text(item["title"],"")
            #button.set_alignment(0,0,1,1)
            #button.set_markup(True)
            #button = gtk.Button(item["title"])
            #button.set_alignment(0,0)
            #label = button.child
            #label.set_markup(item["title"])
            #label.modify_font(pango.FontDescription("sans 16"))
            #button.connect("clicked", self.button_clicked, self, self.window, key, index)
            #self.vboxFeed.pack_start(button, expand=False)
            #index=index+1
        
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