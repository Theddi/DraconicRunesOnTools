from tkinter import *
from tkinter.ttk import *
from draconicrunes import RuneScraper
import argparse
import json
from functools import partial
import os
import webbrowser

class SetEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, set):
            return list(obj)
        return json.JSONEncoder.default(self, obj)
    
#parser = argparse.ArgumentParser(description='Draconic Runes Spell Manager')
#parser.add_argument('-a', '--automatic', action='store_true', help='Executes with setup file')
#args = parser.parse_args()

class drGUI():
    def __init__(self, headless=False):
        self.window = Tk()
        self.window.title("Draconic Runes GUI")
        mainframe = Frame(self.window)
        self.standard_font = ("Arial", 10)
        self.title_font = ("Arial", 12, "bold")
        
        self.RuneScraper = RuneScraper(headless=headless)
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
        
        self.maxCol = 0
        self.save_setup_button = Button(mainframe, text="Save Setup", command=self._saveSetup)
        self.save_setup_button.grid(row=1, column=self.maxCol)
        self.maxCol += 1

        self.classes = self.RuneScraper.getClasses()
        self.class_label = Label(mainframe, text="Class:")
        self.class_label.grid(row=1, column=self.maxCol)
        self.maxCol += 1
        self.class_selector = Combobox(mainframe, values=self.classes)
        self.class_selector.grid(row=1, column=self.maxCol)
        self.maxCol += 1
        self.class_selector.bind("<<ComboboxSelected>>", self._updateClass)

        self.spells_button = Button(mainframe, text="Show Spells", command=self._addSpells)
        self.spells_button.grid(row=1, column=self.maxCol)
        self.maxCol += 1

        self.display_button = Button(mainframe, text="Display Runes", command=self._toggleRunesFrame)
        self.display_button.grid(row=1, column=self.maxCol)
        self.maxCol += 1

        if not headless:
            self.close_button = Button(mainframe, text="Close Browser", command=self.RuneScraper._exitDriver)
            self.close_button.grid(row=1, column=self.maxCol)
            self.maxCol += 1

        self.rune_values = {}
        self.rune_boxes = {}
        self.runes_frame = Frame(mainframe, relief="groove", borderwidth=2)
        for rune_type, rune_dict in self.runes.items():
            rune_type_frame = LabelFrame(self.runes_frame, text=rune_type, relief="groove", borderwidth=2)
            for rune in rune_dict:
                self.rune_values[rune] = BooleanVar(value=False)
                action = partial(self._selectRuneFilter, rune, rune_type)
                self.rune_boxes[rune] = Checkbutton(rune_type_frame, text=rune, onvalue=True, offvalue=False, variable=self.rune_values[rune], command=action)
                self.rune_boxes[rune].pack(side=TOP, anchor=W)
            rune_type_frame.pack(fill=BOTH, side=LEFT)
        self.runes_frame.grid(row=2, column=0, columnspan=self.maxCol+1)
        
        if os.path.exists('setup.json'):
            self._updateSetup()

        self.spells = []
        self.spells_frame = Frame(mainframe, relief="groove", borderwidth=2, height=500)
        self.spells_frame.grid(row=3, column=0, columnspan=self.maxCol+1)

        scrollbar = Scrollbar(self.spells_frame)
        scrollbar.pack(side=RIGHT, fill=Y)
        self.spellcontainer = Canvas(self.spells_frame, yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.spellcontainer.yview)
        self.spellcontainer.pack(side=LEFT, fill=BOTH)

        self.label = Label(mainframe, text="Draconic Runes GUI", font=self.title_font)
        self.label.grid(row=0, column=0, columnspan=self.maxCol+1)

        spell_label = Label(self.spellcontainer, text="Loading...", font=self.title_font)
        self.spells.append({"Load": spell_label})
        mainframe.pack()

        self._addSpells()
        self.window.mainloop()

    def _initRunes(self):
        with open('runes.json') as file:
            return json.load(file)

    def _saveCookies(self):
        self.RuneScraper.save_cookies()
    
    def _saveSetup(self):
        with open('setup.json', 'w') as file:
            json.dump(self.setup, file, cls=SetEncoder)

    def _toggleRunesFrame(self):
        if self.runes_frame.winfo_ismapped():
            self.runes_frame.grid_forget()
        else:
            self.runes_frame.grid(row=2, column=0, columnspan=self.maxCol+1)

    def _updateSetup(self):
        with open('setup.json') as file:
            data = json.load(file)
            data = {k: set(v) if k != "class" and k != "duration" else v for k, v in data.items()}
            
            selClass = data["class"]
            self.class_selector.set(selClass)
            self._updateClass(selClass)
            for rune_type, values in data.items():
                if rune_type == "class":
                    continue
                for rune, val in self.runes[rune_type].items():
                    if type(val) == list:
                        for v in val:
                            if v in values:
                                self.rune_values[rune].set(True)
                                self.RuneScraper.updateElement(rune_type, v, True)
                                
                    else:
                        if val in values:
                            self.rune_values[rune].set(True)
                            self.RuneScraper.updateElement(rune_type, val, True)
                            
            self.setup = data

    def _updateClass(self, event):
        self.RuneScraper.updateElement("class", self.class_selector.get(), True)
        if len(self.setup["class"]):
            self.RuneScraper.updateElement("class", self.setup["class"], False)
        self.setup["class"] = self.class_selector.get()
        
    def _selectRuneFilter(self, rune, rune_type):
        if self.rune_values[rune].get():
            match rune_type:
                case "area":
                    self.setup[rune_type].update(self.runes[rune_type][rune])
                    for v in self.runes[rune_type][rune]:
                        self.RuneScraper.updateElement(rune_type, v, True)
                case "duration":
                    self.setup[rune_type].append(self.runes[rune_type][rune])
                    self.RuneScraper.updateElement(rune_type, self.runes[rune_type][rune], True)
                case _:
                    self.setup[rune_type].add(self.runes[rune_type][rune])
                    self.RuneScraper.updateElement(rune_type, self.runes[rune_type][rune], True)
            print("+"+rune)
        else:
            match rune_type:
                case "area":
                    for v in self.runes[rune_type][rune]:
                        if v in self.setup[rune_type]:
                            self.setup[rune_type].remove(v)
                            self.RuneScraper.updateElement(rune_type, v, False)
                case _:
                    self.setup[rune_type].remove(self.runes[rune_type][rune])
                    self.RuneScraper.updateElement(rune_type, self.runes[rune_type][rune], False)
            print("-"+rune)
        print(self.setup)

    def _addSpells(self):
        for spell in self.spells:
            for widget in spell.values():
                widget.destroy()
        self.spells.clear()
        spellData = self.RuneScraper.getSpells()       
        for idx, spell in enumerate(spellData):
            spell_dict = {}
            idy = 0
            for key, value in spell.items():
                if key == "Link":
                    continue
                spell_label = Label(self.spellcontainer, text=value, 
                                    font=self.standard_font if idx != 0 else self.title_font,
                                    cursor="hand2" if idx != 0 and key == "Name" else None)
                spell_dict[key] = spell_label
                if idx != 0 and key == "Name":
                    href = partial(webbrowser.open, spell["Link"])
                    spell_label.bind("<ButtonRelease-1>", href)
                spell_label.grid(row=idx, column=idy)
                idy += 1
            self.spells.append(spell_dict)
gui = drGUI(True)