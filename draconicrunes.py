import webbrowser
import random
import time
import win32gui
import win32con
import requests
from selenium import webdriver
from selenium.webdriver.support.ui import Select
import os
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
import pickle

class RuneScraper():
    def __init__(self, url="http://127.0.0.1:5000/", headless=False):
        self.url = url
        self.driver = self._getDriver(headless)
        self._startWebsite(self.url+"spells.html")
        self._load_cookies()
        self.driver.find_element(By.XPATH, "//button[text()='Reset']").click()
        self.driver.find_element(By.XPATH, "//button[text()='Filter']").click()
        self.typeToTools = {
            "class": "Class", 
            "area": "Area Style", 
            "component": "Components & Miscellaneous", 
            "damage": "Damage Type", 
            "duration": "Duration", 
            "master": "Level", 
            "range": "Range", 
            "school": "School"
        }
        self.toolsElements = {
            "class": self._loadElements("class"),
            "area": self._loadElements("area"),
            "component": dict(filter(lambda pair: pair[1].text == "Verbal" or pair[1].text == "Somatic" or pair[1].text == "Material", self._loadElements("component").items())),
            "damage": self._loadElements("damage"),
            "duration": self._loadElements("duration"),
            "master": self._loadElements("master"),
            "range": self._loadElements("range"),
            "school": self._loadElements("school")
        }

        self.activeRanges = {
            "5ft-30ft": False,
            "60ft-90ft": False,
            "120ft-500ft": False,
            "1+ Mile": False
        }
        self.durations = ["Instant", "1 Round", "1 Minute", "10 Minutes", "1 Hour", "8 Hours", "24+ Hours", "Permanent", "Special"]

    def _getDriver(self, headless):
        options = webdriver.FirefoxOptions()
        if headless:
            options.add_argument("--headless")
        return webdriver.Firefox(options=options)
    
    def _startWebsite(self, url):
        self.driver.get(url)
        time.sleep(.1)
    
    def _exitDriver(self):
        self.save_cookies()
        self.driver.quit()
    
    def save_cookies(self, name="cookies.pkl", location="./"):
        pickle.dump(self.driver.get_cookies(), open(location+name, "wb"))
    
    def _load_cookies(self, name="cookies.pkl", location="./"):
        cookies = pickle.load(open(location+name, "rb"))
        for cookie in cookies:
            self.driver.add_cookie(cookie)
        time.sleep(1)
    
    def updateElement(self, elementType, rune_result, select=True):
        print(f"Update: {elementType}, {rune_result}, {select}")
        if elementType == "range" and rune_result in self.activeRanges:
            if select:
                if True not in self.activeRanges.values():
                    self.toolsElements[elementType]["Point"].click()
                    self.toolsElements[elementType]["Self (Area)"].click()
                self.activeRanges[rune_result] = True
            else:
                self.activeRanges[rune_result] = False
                if True not in self.activeRanges.values():
                    self.toolsElements[elementType]["Point"].click()
                    self.toolsElements[elementType]["Point"].click()
                    self.toolsElements[elementType]["Self (Area)"].click()
                    self.toolsElements[elementType]["Self (Area)"].click()
            print(f"Active Ranges: {self.activeRanges}")
        elif elementType == "duration":
            dur1 = self.toolsElements[elementType][0]
            dur2 = self.toolsElements[elementType][1]
            init = True if dur2.first_selected_option.text == "Special" else False
            if select:
                #if self.durations.index(dur1.first_selected_option.text) > self.durations.index(rune_result[0]):
                dur1.select_by_value(str(self.durations.index(rune_result[0])))
                #if self.durations.index() < self.durations.index(rune_result[1]):
                dur2.select_by_value(str(self.durations.index(rune_result[1])))
            else:
                dur1.select_by_visible_text("Instant")
                dur2.select_by_visible_text("Special")
        else:
            if select:
                self.toolsElements[elementType][rune_result].click()
            else:
                self.toolsElements[elementType][rune_result].click()
                self.toolsElements[elementType][rune_result].click()
    
    def _loadElements(self, elType):
        if elType == "duration":
            return self._loadDurations()
        else:
            element_div = self.driver.find_element(By.XPATH, f"//div[div/span[text()='{self.typeToTools[elType]}']]")
            elementLists = element_div.find_element(By.XPATH, "./following-sibling::div")
            return {element.text : element for element in elementLists.find_elements(By.CSS_SELECTOR, ".fltr__container-pills > .fltr__pill")}
  
    def _loadDurations(self):
        self.driver.find_element(By.XPATH, "//button[text()='Show as Dropdowns']").click()
        dur_div = self.driver.find_element(By.XPATH, "//div[div/span[text()='Duration']]")
        durDropdowns = dur_div.find_element(By.XPATH, "following-sibling::div[2]")
        return [Select(dur) for dur in durDropdowns.find_elements(By.CLASS_NAME, "form-control")]
    
    def getClasses(self):
        return list(self.toolsElements["class"].keys())

    def getSpells(self):
        self.driver.find_element(By.XPATH, "//button[text()='Save']").click()
        self.driver.find_element(By.XPATH, "//button[text()='Level']").click()
        self.driver.find_element(By.XPATH, "//button[text()='Level']").click()
        spellContainer = self.driver.find_element(By.CLASS_NAME, "list.list--stats.spells")
        
        spellItems = spellContainer.find_elements(By.TAG_NAME, "a")
        spells = []
        titles = ["Name", "Level", "Time", "School", "C.", "Range", "Source"]
        spells.append({title: title for title in titles})
        for spellItem in spellItems:
            link = spellItem.get_attribute("href")
            spellSources = spellItem.find_elements(By.TAG_NAME, "span")
            spellDict = {}
            for i in range(len(spellSources)):
                spellDict[titles[i]] = spellSources[i].text
            spellDict["Link"] = link
            spells.append(spellDict)

        self.driver.find_element(By.XPATH, "//button[text()='Filter']").click()
        return spells
        