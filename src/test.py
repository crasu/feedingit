import sys
from PyQt4 import QtGui
from PyQt4 import QtCore
from PyQt4.QtWebKit import QWebView
import rss
from rss import *

from os.path import isfile, isdir
from os import mkdir

class ArticleDisplay(QtGui.QMainWindow):
    def __init__(self, parent, feed, index):
        QtGui.QMainWindow.__init__(self, parent)
        #self.setWindowTitle('Feeding It')
        
        text = feed.getArticle(index)
        self.web = QWebView()
        self.connect(self.web,QtCore.SIGNAL("linkClicked(QUrl)"), self.linkClicked)
        self.web.setHtml(text)
        self.setCentralWidget(self.web)
        self.show()
        
    def linkClicked(self, link):
	self.web.load(link)
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
        
        #self.mainWidget=QtGui.QScrollArea(self) # dummy widget to contain the
                                      # layout manager
        #self.setCentralWidget(self.mainWidget)
        #self.mainLayout=QtGui.QVBoxLayout()
        self.displayFeed()
        #self.mainWidget.setWidget(self.mainLayout)
        self.show()
        
    def displayFeed(self):
	#1 = Working version with QListWidget
	self.articles = []
	self.mainwidget = QtGui.QWidget()
	self.scroll = QtGui.QScrollArea(self)
	self.layout = QtGui.QVBoxLayout(self.mainwidget)
	
        #1 self.widgetList = QtGui.QListWidget(self)
        #1 self.connect(self.widgetList, QtCore.SIGNAL("itemDoubleClicked(QListWidgetItem *)"), self.buttonArticleClicked)
        #self.connect(self.widgetList, QtCore.SIGNAL("currentItemChanged(QListWidgetItem *)"), self.buttonArticleClicked)
        #1 self.widgetList.setProperty("FingerScrollable", True)
        index = 0
        for item in self.feed.getEntries():
	    #1 widgetItem = QtGui.QListWidgetItem(item["title"])
	    #1 self.articles.append(widgetItem)
	    #1 self.widgetList.addItem(widgetItem)
            button = QtGui.QPushButton(item["title"])
            button.setObjectName(str(index))
            self.layout.addWidget(button)
            #button.setFixedHeight(button.sizeHint().height())
            self.connect(button, QtCore.SIGNAL("clicked()"), self.buttonArticleClicked)           
            index = index + 1
        #1 self.setCentralWidget(self.widgetList)
        self.scroll.setWidget(self.mainwidget)
        self.setCentralWidget(self.scroll)
            
    def buttonArticleClicked(self):
        #index = self.articles.index(self.sender())
        index = int(self.sender().objectName())
        #print self.articles.index(item1)
        #print "clicked"
        #index = self.articles.index(item1)
        self.articleDisplay = ArticleDisplay(self, self.feed, index)

class FeedingIt(QtGui.QMainWindow):    
 
    def __init__(self, parent=None):
        QtGui.QMainWindow.__init__(self, parent)
        self.setWindowTitle('Feeding It')

        update = QtGui.QAction('Update All Feeds', self)
        update.setStatusTip('Update all feeds')
        self.connect(update, QtCore.SIGNAL('triggered()'), self.updateAllFeeds)
        menubar = self.menuBar()
        file = menubar.addAction(update)
        
        add = QtGui.QAction('Add Feed', self)
        self.connect(add, QtCore.SIGNAL('triggered()'), self.addFeedButtonClicked)
        file = menubar.addAction(add)

        # Create MenuBar
        exitAction = QtGui.QAction('Exit', self)
        self.connect(exitAction, QtCore.SIGNAL('triggered()'), self.close)
        file = menubar.addAction(exitAction)
        
        self.listing=Listing()
        self.displayListing() 
        self.show()
        
    def updateAllFeeds(self):
        self.listing.updateFeeds()
        self.displayListing()
        
    def displayListing(self):
        self.mainWidget=QtGui.QWidget(self) # dummy widget to contain the
                                      # layout manager
        self.setCentralWidget(self.mainWidget)
        self.mainLayout=QtGui.QVBoxLayout(self.mainWidget)
        
        for key in self.listing.getListOfFeeds():
            # Create the button for the feed
            button = QtGui.QPushButton(self.listing.getFeedTitle(key), self)
            button.setObjectName(key)
            self.mainLayout.addWidget(button)
            self.connect(button, QtCore.SIGNAL("clicked()"), self.buttonFeedClicked)
        self.show()
            
    def displayFeed(self, qtKey):
        key = str(qtKey)
        self.feedDisplay = FeedDisplay(self.listing.getFeed(key), self.listing.getFeedTitle(key), self)
        
    def buttonFeedClicked(self):
        key = self.sender().objectName()
        self.displayFeed(key)
        
    def addFeedButtonClicked(self):
	 # Ask for Feed Name
	 (title,ok) = QtGui.QInputDialog.getText(self, "Add Feed", "Enter the name of the new feed")
	 if ok and title != "":
	    (url, ok) = QtGui.QInputDialog.getText(self, "Add Feed", "Enter the URL of the new feed")
	    if ok and url != "":
	       self.listing.addFeed(title, url)
	 self.displayListing()
        
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
 
    #Starting the application's main loop
    sys.exit(app.exec_())