#!/usr/local/bin/python3
# -*- coding: utf-8 -*-

import datetime
import subprocess
import os
import random
import xml.etree.ElementTree as ET
import math
import configparser
import pdfkit
from tkinterhtml import HtmlFrame
from tkinter import *
from tkinter import ttk
from tkinter.filedialog import askopenfilename, asksaveasfile, asksaveasfilename
from tkinter.messagebox import showwarning

class MainWindow(ttk.Frame):

    @classmethod
    def main(cls):
        NoDefaultRoot()
        root = Tk()
        root.title("Schussbildanalyse")
        app = cls(root)
        app.grid(sticky=N+S+E+W)
        root.grid_columnconfigure(0, weight=1)
        root.grid_rowconfigure(0, weight=1)
        root.resizable(True, True)
        root.mainloop()

    def __init__(self, root):
        super().__init__(root)
        self.root = root
        self.create_variables()
        self.create_widgets()
        self.grid_widgets()

    def create_variables(self):
        self.shooterList = []
        self.selectedShooter = StringVar(self, '')
        self.selectedPane = StringVar(self, '')
        self.paneSizeOptions = [('Luftgewehr', 'LG'), ('Luftpistole', 'LP')]
        self.paneSize = StringVar(self, self.paneSizeOptions[0][1])
        self.metrics = StringVar(self, '')
        self.canvasWidth = 200
        self.canvasHeight = 200
        self.bulletSize = 4.5
        self.results = []

    def create_widgets(self):
        self.canvas = Canvas(self.root)
        self.sidebareFrame = ttk.Frame(self.root)
        self.loadFileButton = ttk.Button(self.sidebareFrame, text='Ergebnisse laden', command=self.loadFile)
        self.loadFileButton.pack(fill=X)
        for text, mode in self.paneSizeOptions:
            b = ttk.Radiobutton(self.sidebareFrame, text=text, variable=self.paneSize, value=mode, command=self.drawPane)
            b.pack(anchor=W)
        self.shooterDropdown = OptionMenu(self.sidebareFrame, self.selectedShooter, "")
        self.shooterDropdown.pack(fill=X)
        self.paneList = Listbox(self.sidebareFrame, exportselection=False)
        self.paneList.pack(fill=Y, expand=YES)
        self.paneList.bind('<<ListboxSelect>>', self.paneSelectionChanged)
        self.metricOutput = Text(self.root, height=10)


    def grid_widgets(self):
        self.canvas.grid(column=0, row=0, sticky=N+E+S+W)
        self.canvas.bind("<Configure>", self.resized)
        self.sidebareFrame.grid(column=1, row=0, sticky=N+S)
        self.metricOutput.grid(column=0, row=1, columnspan=2, sticky=W+E)

    def loadFile(self):
        initdir = os.getcwd()
        if (os.path.exists("/var/shootmaster/ERGEBNIS/XML")):
            intidir = "/var/shootmaster/ERGEBNIS/XML"
        filename = askopenfilename(initialdir = initdir, parent = self.root, title = "Datei auswählen", filetypes = [("xml","*.xml")])
        if filename: self.parseResultFile(filename)

    def parseResultFile(self, filename):
        tree = ET.parse(filename)
        root = tree.getroot()
        self.results = []
        for child in root:
            shooter = {}
            shooter["targetID"] = child.attrib["TargetID"]
            shooter["gender"] = child.find("Shooter").find("Gender").text
            shooter["class"] = child.find("MatchClass").find("Name").text
            shooter["club"] = child.find("Club").find("Name").text
            shooter["lastname"] = child.find("Shooter").find("FamilyName").text
            shooter["firstname"] = child.find("Shooter").find("GivenName").text
            shooter["shots"] = []
            for aiming in child.find("Aimings").find("AimingData").iter("Shot"):
                shot = {}
                shot["timestamp"] = aiming.find("TimeStamp").find("DateTime").text.replace("T", " ").replace("Z", "")
                shot["resolution"] = aiming.find("Coordinate").find("CCoordinate").attrib["Resolution"]
                shot["x"] = aiming.find("Coordinate").find("CCoordinate").find("X").text
                shot["y"] = aiming.find("Coordinate").find("CCoordinate").find("Y").text
                shot["factor"] = self.getDistance(0,0,shot["x"],shot["y"])
                shooter["shots"].append(shot)
            self.results.append(shooter)
        self.updateShooterDropdown()
        self.updatePaneList()

    def updateShooterDropdown(self):
        self.shooterDropdown.children["menu"].delete(0, "end")
        self.shooterList = []
        for shooter in self.results:
            name = shooter["firstname"] + " " + shooter["lastname"]
            if (name not in self.shooterList):
                self.shooterList.append(name)
        self.shooterList = sorted(self.shooterList)
        for shooter in self.shooterList:
            self.shooterDropdown.children["menu"].add_command(label=shooter, command=lambda value=shooter: self.updatePaneList(value))
        self.selectedShooter.set(next(iter(self.shooterList)))

    def updatePaneList(self, shooter=None):
        if shooter == None:
            shooter = self.shooterList[0]
        self.selectedShooter.set(shooter)
        self.paneList.delete(0,'end')
        self.panes = []
        for pane in self.results:
            if (pane["firstname"] + " " + pane["lastname"] == shooter):
                self.panes.append(pane["shots"][0]["timestamp"])
        self.panes = sorted(self.panes)
        for pane in self.panes:
            self.paneList.insert(END, pane)
        self.paneList.selection_set(0)
        self.paneSelectionChanged(index=0)

    def paneSelectionChanged(self, event=None, index=None):
        if event != None:
            self.selectedPane.set(self.paneList.get(event.widget.curselection()))
        if index != None:
            self.selectedPane.set(self.paneList.get(index))
        result = {}
        self.drawPane()

    def drawResult(self, result):
        bulletRadius = self.bulletSize / 2 * self.resizeFactor
        i = 1
        for shot in result["shots"]:
            x = int(shot["x"]) / int(shot["resolution"]) * self.resizeFactor + self.canvasWidth / 2
            y = (int(shot["y"]) / int(shot["resolution"]) * self.resizeFactor * -1) + self.canvasHeight / 2
            currentOffset = self.getDistance(0, 0 , int(shot["x"]) / int(shot["resolution"]), int(shot["y"]) / int(shot["resolution"])) * 100
            color = "blue"
            fill = "white"
            if currentOffset < (500 if self.paneSize.get() == "LG" else 1600):
                color = "yellow"
                fill = "black"
            if currentOffset < (250 if self.paneSize.get() == "LG" else 800): 
                color = "red"
            self.canvas.create_oval(x - bulletRadius, y - bulletRadius, x + bulletRadius, y + bulletRadius, fill=color)
            self.canvas.create_text(x, y, text=str(i), fill=fill)
            i = i + 1

    def evaluateResult(self, result):
        self.metricOutput.delete("1.0", END)
        factor = "Teiler:\t"
        value = "Wert:\t"
        header = "Schuss:\t"
        dist = 0
        bestFactor = 0
        bestValue = 0
        bestShot = 0
        i = 0
        for shot in result["shots"]:
            i = i + 1
            val = round(11 - shot["factor"] / (250 if self.paneSize.get() == "LG" else 800), 2)
            fact = round(shot["factor"], 2)
            dist = dist + shot["factor"] ** 2
            if val > bestValue: 
                bestValue = val
                bestShot = i
                bestFactor = fact
            header = header + str(i) + "\t"
            value = value + str(val) + "\t"
            factor = factor + str(fact) + "\t"
        # TODO create text
        self.metricOutput.insert(END, header + "\n" + value + "\n" + factor + "\n\n")
        self.metricOutput.insert(END, "Distanzindikator: " + str(round(dist ** 0.5)) + "\n")
        self.metricOutput.insert(END, "Bester Schuss: " + str(bestShot) + " (Wert: " + str(bestValue) + " , Teiler: " + str(bestFactor) + ")\n")

    def resized(self, event):
        self.canvasWidth = event.width
        self.canvasHeight = event.height
        self.drawPane()

    def zoomIn(self, event):
        resizeFactor = self.resizeFactor * 1.2
        self.drawPane(resizeFactor)
    
    def zoomOut(self, event):
        resizeFactor = self.resizeFactor * 0.8
        self.drawPane(resizeFactor)

    def drawPane(self, resizeFactor=None):
        result = None
        for pane in self.results:
            if (pane["firstname"] + " " + pane["lastname"] == self.selectedShooter.get() and pane["shots"][0]["timestamp"] == self.selectedPane.get()):
                result = pane
        maxOffset = 0
        if result != None:
            for shot in result["shots"]:
                currentOffset = self.getDistance(0, 0 , int(shot["x"]) / int(shot["resolution"]), int(shot["y"]) / int(shot["resolution"])) + self.bulletSize / 2
                if abs(currentOffset) > maxOffset:
                    maxOffset = currentOffset
        self.canvas.delete("all")
        if self.paneSize.get() == "LG":
            self.drawLGPane(outerDiameter=maxOffset * 2, resizeFactor=resizeFactor)
        if self.paneSize.get() == "LP":
            self.drawLPPane(outerDiameter=maxOffset * 2, resizeFactor=resizeFactor)
        if result != None:
            self.drawResult(result=result)
            self.evaluateResult(result=result)
        buttonZoomIn = self.canvas.create_rectangle(5, 5, 25, 25, outline="black", fill="white")
        bootonZoomInText = self.canvas.create_text(15, 15, text="+")
        self.canvas.tag_bind(buttonZoomIn, "<Button-1>", self.zoomIn)
        self.canvas.tag_bind(bootonZoomInText, "<Button-1>", self.zoomIn)
        buttonZoomOut = self.canvas.create_rectangle(5, 25, 25, 45, outline="black", fill="white")
        bootonZoomOutText = self.canvas.create_text(15, 35, text="-")
        self.canvas.tag_bind(buttonZoomOut, "<Button-1>", self.zoomOut)
        self.canvas.tag_bind(bootonZoomOutText, "<Button-1>", self.zoomOut)

    def drawLGPane(self, outerDiameter=45.5, resizeFactor=None):
        rings = [0.25, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5]
        if outerDiameter == None  or outerDiameter == 0:
            outerDiameter = 45.5
        innerDiameter = 30.5
        self.drawGenericPane(rings, innerDiameter, outerDiameter, resizeFactor)

    def drawLPPane(self, outerDiameter=155.5, resizeFactor=None):
        rings = [2.5, 3.25, 8, 8, 8, 8, 8, 8, 8, 8, 8]
        if outerDiameter == None or outerDiameter == 0:
            outerDiameter = 155.5
        innerDiameter = 59.5
        self.drawGenericPane(rings, innerDiameter, outerDiameter, resizeFactor)

    def drawGenericPane(self, rings, innerDiameter, outerDiameter, resizeFactor=None):
        if resizeFactor == None:
            self.resizeFactor = min(self.canvasWidth - 10, self.canvasHeight - 10) / outerDiameter
        else:
            self.resizeFactor = resizeFactor

        # Draw inner diameter
        self.canvas.create_oval(self.canvasWidth / 2 - innerDiameter * self.resizeFactor / 2, self.canvasHeight / 2 - innerDiameter * self.resizeFactor / 2, self.canvasWidth / 2 + innerDiameter * self.resizeFactor / 2, self.canvasHeight / 2 + innerDiameter * self.resizeFactor / 2, fill='gray75', outline='')

        # Draw rings
        offset = sum(rings)
        for i in range(len(rings)):
            self.canvas.create_oval(self.canvasWidth / 2 - offset * self.resizeFactor, self.canvasHeight / 2 - offset * self.resizeFactor, self.canvasWidth / 2 + offset * self.resizeFactor, self.canvasHeight / 2 + offset * self.resizeFactor)
            if i < 9:
                self.canvas.create_text(self.canvasWidth / 2, self.canvasHeight / 2 - offset * self.resizeFactor + rings[-i-1] / 2 * self.resizeFactor, text=str(i + 1))
                self.canvas.create_text(self.canvasWidth / 2, self.canvasHeight / 2 + offset * self.resizeFactor - rings[-i-1] / 2 * self.resizeFactor, text=str(i + 1))
                self.canvas.create_text(self.canvasWidth / 2 - offset * self.resizeFactor + rings[-i-1] / 2 * self.resizeFactor, self.canvasHeight / 2, text=str(i + 1))
                self.canvas.create_text(self.canvasWidth / 2 + offset * self.resizeFactor - rings[-i-1] / 2 * self.resizeFactor, self.canvasHeight / 2, text=str(i + 1))
            offset = offset - rings[-i-1]
    
    def getDistance(self, x1, y1, x2, y2):
        dx = int(x1) - int(x2)
        dy = int(y1) - int(y2)
        return math.sqrt(dx * dx + dy * dy)

if __name__ == '__main__':
    MainWindow.main()