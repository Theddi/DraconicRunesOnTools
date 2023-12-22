from tkinter import *
from tkinter.ttk import *
import pandas as pd
from pandastable import Table, TableModel
import argparse
import json
from functools import partial
import os
import webbrowser
import csv
import re
csv.field_size_limit(2147483647)

class SetEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, set):
            return list(obj)
        return json.JSONEncoder.default(self, obj)

class drGUI():
    def __init__(self):
        self.window = Tk()
        self.window.title("Draconic Runes GUI")
        self.window.geometry("1545x1000")
        self.standard_font = ("Arial", 10)
        self.title_font = ("Arial", 12, "bold")
        
        self.setup = {
                "class": "",
                "area": set(),
                "component": set(),
                "damage": set(),
                "school": set(),
                "duration": [],
                "master": set(),
                "range": set()
                }
        self.runes = self._initRunes()
        
        self.filter_frame = Frame(self.window)
        self.save_setup_button = Button(self.filter_frame, text="Save Setup", command=self._saveSetup)
        self.save_setup_button.grid(row=0, column=0, sticky="w")

        self.classes = self._getClasses()
        self.class_label = Label(self.filter_frame, text="Class:")
        self.class_label.grid(row=0, column=1, sticky="n")
        self.class_selector = Combobox(self.filter_frame, values=self.classes, state="readonly")
        self.class_selector.grid(row=0, column=2, sticky="n")
        self.class_selector.bind("<<ComboboxSelected>>", self._updateClass)

        self.display_button = Button(self.filter_frame, text="Display Runes", command=self._toggleRunesFrame)
        self.display_button.grid(row=0, column=3, sticky="e")

        self.rune_values = {}
        self.rune_boxes = {}
        self.runes_frame = Frame(self.filter_frame, relief="groove", borderwidth=2)
        for rune_type, rune_dict in self.runes.items():
            rune_type_frame = LabelFrame(self.runes_frame, text=rune_type, relief="groove", borderwidth=2)
            for rune in rune_dict:
                self.rune_values[rune] = BooleanVar(value=False)
                action = partial(self._selectRuneFilter, rune, rune_type)
                self.rune_boxes[rune] = Checkbutton(rune_type_frame, text=rune, onvalue=True, offvalue=False, variable=self.rune_values[rune], command=action)
                self.rune_boxes[rune].pack(side=TOP, anchor=W)
            rune_type_frame.pack(fill=BOTH, side=LEFT)
        self.runes_frame.grid(row=1, column=0, columnspan=4)
        self.filter_frame.pack(side=TOP, anchor="n")

        if os.path.exists('setup.json'):
            self._updateSetup()

        self.spellItems = []
        self.spellList = self._loadSpells()
        self.curList = None
        self._getSpells(False)

        self.spells_frame = Frame(self.window, relief="groove", borderwidth=2)
        self.spells_frame.pack(side=BOTTOM, anchor="s", fill=BOTH, expand=True)

        self.spellsort = 1
        self.spellcontainer = Table(self.spells_frame, dataframe=self.curList, showstatusbar=True)
        self.spellcontainer.sortTable(self.spellsort)
        self.spellcontainer.show()
        self.spellcontainer.hideRowHeader()

        self.window.mainloop()

    def _initRunes(self):
        with open('runes.json') as file:
            return json.load(file)

    def _saveSetup(self):
        with open('setup.json', 'w') as file:
            json.dump(self.setup, file, cls=SetEncoder)

    def _toggleRunesFrame(self):
        if self.runes_frame.winfo_ismapped():
            self.runes_frame.grid_forget()
        else:
            self.runes_frame.grid(row=2, column=0, columnspan=self.maxCol+1)

    def _getClasses(self):
        with open('classes.csv', newline='\n', encoding="utf8") as csvfile:
            classreader = csv.reader(csvfile, delimiter=',', quotechar='"')
            classes = []
            for row in classreader:
                classes.append(row[0])
            return classes
    
    def remove_parentheses(self, text):
        return re.sub(r'\([^)]*\)', '', text)

    def _loadSpells(self):
        spells = pd.read_csv('spells.csv')

        spells["Components"] = spells["Components"].apply(self.remove_parentheses)
        spells = spells[~spells["Level"].str.contains("cantrip", case=False, na=False)]
        spells["Link"] = spells["Name"]+"_"+spells["Source"]
        return spells

    def _getSpells(self, redraw=True):
        def invalid(option):
            print(f"Option {option} has to be set")
            self.curList = None
            if redraw:
                self.spellcontainer.updateModel(TableModel(self.curList))
                self.spellcontainer.redraw()

        '''"class": "",
                "area": set(),
                "damage": set(),
                "duration": [],'''
        spells = self.spellList
        # Filter required runes and class
        if len(self.setup["class"]):
            spells = spells[spells["Classes"].str.contains(self.setup["class"], case=False, na=False)]
        else:
            invalid("class")
            return

        if len(self.setup["master"]):
            spells = spells[spells["Level"].isin(self.setup["master"])]
        else:
            invalid("master")
            return

        if len(self.setup["school"]):
            spells = spells[spells["School"].isin(self.setup["school"])]
        else:
            invalid("school")
            return
        
        # Filter additional runes
        spells["RuneCount"] = 0    
        def component_check(row):
            count = 0
            for rune in self.setup["component"]:
                if rune in row["Components"]:
                    count += 1
            return count
        if len(self.setup["component"]):
            spells["RuneCount"] += spells.apply(component_check, axis=1)

        def range_check(row):
            if "Self" == row:
                if "Self" in self.setup["range"]:
                    return 1
                else:
                    return 0
            if "Touch" == row:
                if "Touch" in self.setup["range"]:
                    return 1
                else:
                    return 0
            elif "mile" in row or "Unlimited" in row: 
                if self.runes["range"]["Terra"] in self.setup["range"]:
                    return 1
                else:
                    return 0
            else:
                num = re.findall(r'\d+', row)
                if "(" in row:
                    print(num)
                for rang in self.setup["range"]:
                    if "Mile" in rang or "Self" in rang or "Touch" in rang:
                        continue
                    selRange = re.findall(r'\d+', rang)
                    if len(num) and int(num[0]) in range(int(selRange[0]), int(selRange[1])+1):
                        return 1
            return 0
        if len(self.setup["range"]):
            spells["RuneCount"] += spells["Range"].apply(range_check)
        
        spells = spells[["Name", "Level", "School", "Casting Time", "Range", "Components", "Duration", "Source", "RuneCount"]]
        self.curList = spells
        if redraw:
            self.spellcontainer.updateModel(TableModel(self.curList))
            self.spellcontainer.sortTable(self.spellsort)
            self.spellcontainer.redraw()

    def _updateSetup(self):
        with open('setup.json') as file:
            data = json.load(file)
            data = {k: set(v) if k != "class" and k != "duration" else v for k, v in data.items()}
            
            for rune_type, values in data.items():
                if rune_type == "class":
                    self.class_selector.set(values)
                    self.setup["class"] = values
                    continue
                for rune, val in self.runes[rune_type].items():
                    if type(val) == list:
                        for v in val:
                            if v in values:
                                self.rune_values[rune].set(True)
                    else:
                        if val in values:
                            self.rune_values[rune].set(True)
                            
            self.setup = data

    def _updateClass(self, event):
        self.setup["class"] = self.class_selector.get()
        self._getSpells(True)
        
    def _getSelectedClass(self):
        return self.class_selector.get()

    def _selectRuneFilter(self, rune, rune_type):
        if self.rune_values[rune].get():
            match rune_type:
                case "area":
                    self.setup[rune_type].update(self.runes[rune_type][rune])
                case "duration":
                    self.setup[rune_type].append(self.runes[rune_type][rune])
                case _:
                    self.setup[rune_type].add(self.runes[rune_type][rune])
            print("+"+rune)
        else:
            match rune_type:
                case "area":
                    for v in self.runes[rune_type][rune]:
                        if v in self.setup[rune_type]:
                            self.setup[rune_type].remove(v)
                case _:
                    self.setup[rune_type].remove(self.runes[rune_type][rune])
            print("-"+rune)
        self._getSpells(True)
gui = drGUI()