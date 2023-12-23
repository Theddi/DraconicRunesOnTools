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

        def on_cell_click(event, table):
            row = table.getSelectedRow()
            col = table.getSelectedColumn()
            if col == 0:
                url = table.model.df.iloc[row, 8]
                webbrowser.open_new(url)

        class ClickableTable(Table):
            def handle_left_click(self, event):
                super().handle_left_click(event)
                self.cell_click_function(event)

        self.spellsort = 8
        self.spellcontainer = ClickableTable(self.spells_frame, dataframe=self.curList, showstatusbar=True)
        if self.curList is not None:
            self.spellcontainer.sortTable(self.spellsort, False)
        self.spellcontainer.show()
        self.spellcontainer.cell_click_function = lambda event: on_cell_click(event, self.spellcontainer)
        self.spellcontainer.editable = False
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
            self.runes_frame.grid(row=1, column=0, columnspan=4)

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
        spells["School"] = spells["School"].apply(lambda x: x.split(" ")[0])
        spells["Components"] = spells["Components"].apply(self.remove_parentheses)
        spells = spells[~spells["Level"].str.contains("cantrip", case=False, na=False)]
        
        def update_link(row):
            if row["Source"] != "HGtMH":
                return "https://5e.tools/spells.html#" + row["Name"] + "_" + row["Source"]
            else:
                return "https://5e.tools/spells.html#" + row["Name"] + "_" + "helianasguidetomonsterhunting"

        # Anwendung der Funktion auf die Daten
        spells["Link"] = spells.apply(lambda row: update_link(row), axis=1)
        return spells

    def _getSpells(self, redraw=True):
        def invalid(option):
            print(f"Option {option} has to be set")
            self.curList = None
            if redraw:
                self.spellcontainer.updateModel(TableModel(self.curList))
                self.spellcontainer.redraw()

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
        
        def duration_check(row):
            for dur in self.setup["duration"]:
                if dur == self.runes["duration"]["Dubito"]:
                    if "round" in row:
                        if int(re.findall(r'\d+', row)[0]) < 10: 
                            return 1
                elif dur == self.runes["duration"]["Praxis"]:
                    if dur[0] in row or dur[1] in row: return 1
                elif dur == self.runes["duration"]["Subita"]:
                    if "Instantaneous" in row: return 1
                elif dur == self.runes["duration"]["Mensis"]:
                    if "day" in row:
                        num = int(re.findall(r'\d+', row)[0])
                        less = int(re.findall(r'\d+', dur[0])[0])
                        more = int(re.findall(r'\d+', dur[1])[0])
                        if num >= less and num <= more: return 1
                elif dur == self.runes["duration"]["Occasus"]:
                    if "hour" in row:
                        num = int(re.findall(r'\d+', row)[0])
                        less = int(re.findall(r'\d+', dur[0])[0])
                        more = int(re.findall(r'\d+', dur[1])[0])
                        if num >= less and num <= more: return 1
                elif dur == self.runes["duration"]["Proelium"]:
                    if "minute" in row:
                        num = int(re.findall(r'\d+', row)[0])
                        less = int(re.findall(r'\d+', dur[0])[0])
                        more = int(re.findall(r'\d+', dur[1])[0])
                        if num >= less and num <= more: return 1
                elif dur == self.runes["duration"]["Solis"]:
                    if "hour" in row:
                        num = int(re.findall(r'\d+', row)[0])
                        less = int(re.findall(r'\d+', dur[0])[0])
                        more = int(re.findall(r'\d+', dur[1])[0])
                        if num >= less and num <= more: return 1
            return 0
        if len(self.setup["duration"]):
            spells["RuneCount"] += spells["Duration"].apply(duration_check)

        def damage_check(row):
            for dmg in self.setup["damage"]:
                test = re.findall(r'\d '+ dmg.lower() + " damage", row)
                if len(test):
                    return 1
            return 0
        if len(self.setup["damage"]):
            spells["RuneCount"] += spells["Text"].apply(damage_check)

        def area_check(row):
            for a in self.setup["area"]:
                print(a)
                test = re.findall(r''+a.lower(), row)
                if len(test):
                    return 1
            return 0
        if len(self.setup["area"]):
            spells["RuneCount"] += spells["Text"].apply(area_check)
        
        spells = spells[spells["RuneCount"] >= spells["Level"].apply(lambda x: float(re.findall(r'\d+', x)[0])/3)]
        spells = spells[["Name", "Level", "School", "Casting Time", "Range", "Components", "Duration", "Source", "Link"]]
        self.curList = spells
        print(self.setup)
        if redraw:
            self.spellcontainer.updateModel(TableModel(self.curList))
            self.spellcontainer.sortTable(self.spellsort, False)
            self.spellcontainer.redraw()
            self.spellcontainer.autoResizeColumns()

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