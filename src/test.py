import sys
from PyQt4 import QtGui
from PyQt4 import QtCore
from PyQt4.QtWebKit import QWebView
import feedparser

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

class RSSReader(QtGui.QMainWindow):    
 
    def __init__(self, parent=None):
        QtGui.QMainWindow.__init__(self, parent)
        self.setWindowTitle('Feeding It')
        self.setGeometry(100,100,300,300)


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
        self.listing.downloadFeeds()
        
        listOfFeeds = QtGui.QListWidget(self.mainWidget)
        
        tmp = ["test","test1", "test2"]
        #for item in self.listing.getListOfFeeds():
        for item in tmp:
            QtGui.QListWidgetItem(item, listOfFeeds)
        
        #layout = QtGui.QVBoxLayout()
        #layout.addWidget(listOfFeeds) 
        #self.setLayout(layout)
 
if __name__ == '__main__':    
 
    #Creating Qt application
    app = QtGui.QApplication(sys.argv)
 
    myRSSReader = RSSReader()
    myRSSReader.show()
 
    #Initing application
    sys.exit(app.exec_())