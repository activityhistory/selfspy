#  CBGraphView.py

from objc import YES, NO, IBAction, IBOutlet
from Foundation import *
from AppKit import *


class CBGraphView(NSControl):
    lineColor = None    # the color to make the bars
    lineWidth = 1.0     # default bar width (1 "pixel")
    lineSpacing = 0.0   # default spacing between bars to no space
    assigned_color = NSColor.whiteColor()   # used to toggle border color on mouse click

    def initWithFrame_(self, frame):
        """ basic constructor for views. here we init colors and gradients """

        self = NSControl.initWithFrame_(self, frame)

        if self:
            self.lineColor = NSColor.colorWithCalibratedRed_green_blue_alpha_(33/255.0, 104/255.0, 198/255.0, 1.0)
            self.borderColor = NSColor.darkGrayColor()
            self.backgroundColor = NSColor.darkGrayColor()
            self.drawBorder = False

        return self

    def setLineWidth_(self, width):
        """ let user change line (bar) width """
        self.lineWidth = width

    def setLineSpacing_(self, spacing):
        """ let user change spacing bewteen bars (lines) """
        self.lineSpacing = spacing

    def setLineColor_(self, color):
        """ let user change line (bar) color """
        self.lineColor = color

    def setBorderColor_(self, color):
        """ let user change border color """
        self.borderColor = color

    def setAssignedColor_(self, color):
        """ let user change border color """
        self.assigned_color = color

    def setBackgroundColor_(self, color):
        self.backgroundColor = color

    def setDrawBorder_(self, drawBorder):
        """ let user change line (bar) width """
        self.drawBorder = drawBorder

    def isOpaque(self):
        """ are we opaque? why, of course we are! """
        return YES

    # TODO fix error that occurs when using super()
    def dealloc(self):
        """ default destructor """
        self.grad.release()
        NSControl.dealloc(self) # super(CBGraphView, self).dealloc()

    def drawRect_(self, rect):
        """ draw the background and border then clip the inner rect """
        bounds = self.bounds() # get our view bounds
        insetBounds = NSInsetRect(bounds, 1, 1) # set the inside portion

        if self.drawBorder:
            self.borderColor.set()
            NSBezierPath.setDefaultLineWidth_(1.0) # set line width for outline
            NSBezierPath.strokeRect_(bounds) # draw outline

        self.backgroundColor.setFill()
        NSBezierPath.fillRect_(bounds)

        # NSBezierPath.clipRect_(insetBounds) # set the clipping path
        # insetBounds.size.height -= 1 # leave room at the top (purely my personal asthetic

    def mouseDown_(self, theEvent):
        """ change border color on mouse click """
        self.toggleBorder()

    def toggleBorder(self):
        """ change border color """
        if self.backgroundColor == self.assigned_color:
            self.setBackgroundColor_(NSColor.redColor())
        else:
            self.setBackgroundColor_(self.assigned_color)

        self.setNeedsDisplay_(True)
