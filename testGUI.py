from tkinter import *
from PIL import Image, ImageTk

class Window(Frame):
    
    """ Create a basic window """
    def __init__(self, master = None):
        Frame.__init__(self, master)
        self.master = master
        
        self.init_window()
    
    """ Name window title and create a menu bar/button """
    def init_window(self):
        self.master.title('testGUI')
        self.pack(fill = BOTH, expand = 1)
        
        # Create cascading menu bar using Menu method in tkinter
        menuBar = Menu(self.master)
        self.master.config(menu=menuBar)
        
        file = Menu(menuBar, tearoff = False) # tearoff causes the dashes to disappear
        file.add_command(label = 'Save')
        file.add_command(label = 'Exit', command = self.client_exit)
        menuBar.add_cascade(label = 'File', menu = file)
        
        edit = Menu(menuBar, tearoff = False)
        edit.add_command(label = 'Undo')
        edit.add_command(label = 'Show Image', command = self.showImg)
        edit.add_command(label = 'Show Text', command = self.showText)
        menuBar.add_cascade(label= 'Edit', menu = edit)
        
        # Create Quit button on the top left hand corner
        #quitButton = Button(self, text = 'Quit', command=self.client_exit)
        #quitButton.place(x=0, y=0)
    
    def showImg(self):
        load = Image.open('Clement.jpg')
        render = ImageTk.PhotoImage(load)
        img = Label(self, image = render)
        img.Image = render
        img.place(x=0, y=0)
    
    def showText(self):
        text = Label(self, text = 'Hi, I am Clement!')
        text.pack()
    
    def client_exit(self):
        exit()
        
root = Tk()
root.geometry("400x300") # Setting size of window
app = Window(root)
root.mainloop()