#
#  CBGraphView.py

from objc import YES, NO, IBAction, IBOutlet
from Foundation import *
from AppKit import *

#import RingBuffer

class CBGraphView(NSControl):

    dataQueue = None     # holds the data we'll be graphing
    gradientGray = None  # the gray color of the black->gray gradient we are using
    lineColor = None     # the color to make the bars
    grad = None          # the gradient object
    lineWidth = 1.0      # default bar width (1 "pixel")
    lineSpacing = 0.0    # default spacing between bars to no space

    current_color = 0

    def initWithFrame_(self, frame):
        """ basic constructor for views. here we init colors and gradients """

        self = NSControl.initWithFrame_(self, frame) # super(CBGraphView, self).initWithFrame_(frame)

        if self:

            self.gradientGray = NSColor.colorWithCalibratedRed_green_blue_alpha_(50/255.0, 50/255.0, 50/255.0, 1.0)
            self.lineColor = NSColor.colorWithCalibratedRed_green_blue_alpha_(33/255.0, 104/255.0, 198/255.0, 1.0)
            self.borderColor = NSColor.blackColor()

            self.grad = NSGradient.alloc().initWithStartingColor_endingColor_(NSColor.blackColor(), self.gradientGray)
            self.grad.retain()

        return self

    def setDataQueue_(self, dq):
        """ set the data object we are graphig """
        self.dataQueue = dq
        self.setNeedsDisplay_(YES)

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

    def setBackgroundColor_(self, color):
        self.backgroundColor = color

    # def setupdateWindowListoundGradient_(self, startColor, endColor):
    #     """ let user change the gradient colors """
    #     self.grad.release()
    #     self.grad = NSGradient.alloc().initWithStartingColor_endingColor_(startColor, endColor)
    #     self.grad.retain()

    def isOpaque(self):
        """ are we opaque? why, of course we are! """
        return YES

    # TODO fix error that occurs when using super()
    def dealloc(self):
        """ default destructor """
        self.grad.release()
        NSControl.dealloc(self) # super(CBGraphView, self).dealloc()

    def drawRect_(self, rect):
        """ we raw the background gradient and graph outline then clip the inner rect
            and draw the bars """

        bounds = self.bounds() # get our view bounds
        insetBounds = NSInsetRect(bounds, 2, 2) # set the inside ortion

        # CGContextRef context = (CGContextRef) [[NSGraphicsContext currentContext] graphicsPort];
        # CGContextSetRGBFillColor(context, 0.227,0.251,0.337,0.8);
        # CGContextFillRect(context, NSRectToCGRect(dirtyRect));

    #     // set any NSColor for filling, say white:
    # [[NSColor whiteColor] setFill];
    # NSRectFill(dirtyRect);
    # [super drawRect:dirtyRect];


        # self.setBackgroundColor_(NSColor.whiteColor())

        # self.setBorderColor_(NSColor.blackColor())

        # currentContext = NSGraphicsContext.currentContext()
        # context = CGContextRef(currentContext)
        # context.CGContextSetRGBFillColor(0.227,0.251,0.337,0.8)
        # dirtyRect = NSRectToCGRect(rect)
        # context.CGContextFillRect(dirtyRect)

        # r = NSBezierPath.bezierPathWithRect_(bounds) # creatre a new bezier rect
        # self.grad.drawInBezierPath_angle_(r, 90.0) # and draw gradient in it

        self.borderColor.set() # set border to white
        NSBezierPath.setDefaultLineWidth_(3.0) # set line width for outline
        NSBezierPath.strokeRect_(bounds) # draw outline

        NSBezierPath.clipRect_(insetBounds) # set the clipping path
        insetBounds.size.height -= 2 # leave room at the top (purely my personal asthetic

        buf = None  # init the list structure we will be using

        if self.dataQueue:
            buf = self.dataQueue.get()  # get teh list

        if buf:

            rbuf = [ q for q in buf if q ] # filter "None" from the list
            rbuf.reverse() # reverse the list

            self.lineColor.set() # set drawing color

            barRect = NSRect() # init the rect

            maxB = max(rbuf) # find out the max value so we can scale the graph

            # disable anti-aliasing since it looks bad
            shouldAA = NSGraphicsContext.currentContext().shouldAntialias()
            NSGraphicsContext.currentContext().setShouldAntialias_(NO)

            # draw each bar

            barRect.origin.x = insetBounds.size.width - self.lineWidth + 2
            for b in rbuf:
                if b:

                    barRect.origin.y = insetBounds.origin.y
                    barRect.size.width = self.lineWidth
                    barRect.size.height = ((int(b) * insetBounds.size.height) / maxB)

                    NSBezierPath.fillRect_(barRect)

                    barRect.origin.x = barRect.origin.x - self.lineWidth - self.lineSpacing

            NSGraphicsContext.currentContext().setShouldAntialias_(shouldAA)

    def mouseDown_(self, theEvent):
        print("mouse button pressed")
        # bounds = self.bounds() # get our view bounds
        # r = NSBezierPath.bezierPathWithRect_(bounds) # creatre a new bezier rect
        # self.grad.drawInBezierPath_angle_(r, 45.0)

        self.current_color = self.current_color % 2 + 1

        if self.current_color == 1:
            self.setBorderColor_(NSColor.blackColor())
        else:
            self.setBorderColor_(NSColor.whiteColor())

        self.setNeedsDisplay_(True)


    def invokeFromOutside(self):
        print("mouse button pressed")
        # bounds = self.bounds() # get our view bounds
        # r = NSBezierPath.bezierPathWithRect_(bounds) # creatre a new bezier rect
        # self.grad.drawInBezierPath_angle_(r, 45.0)

        self.current_color = self.current_color % 2 + 1

        if self.current_color == 1:
            self.setBorderColor_(NSColor.blackColor())
        else:
            self.setBorderColor_(NSColor.whiteColor())

        self.setNeedsDisplay_(True)