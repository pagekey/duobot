#!/usr/bin/env python

URL = "https://www.duolingo.com/"
BRAIN_FILE = "brain.csv"
UPDATE_BRAIN = True
CONFIG_FILE = "config.yml"
SLEEP_NEXT_QUESTION = 1 # seconds

CSS_CLASS_HEADER = '._1KHTi._1OomF'
CSS_CLASS_LANG_ICON = '._3gtu3._1-Eux.iDKFi'
CSS_CLASS_LANG_NAME = '.U_ned'

NATIVE_LANG = "English"
FOREIGN_LANG = "Arabic"

import time, sys, csv, unicodedata, os, datetime
import yaml
import pdb
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException, ElementClickInterceptedException


def load_config():
    # Load username and password from config file
    with open(CONFIG_FILE, 'r') as ymlfile:
        cfg = yaml.load(ymlfile)
    return cfg
def build_brain():
    brain = []
    with open(BRAIN_FILE) as brainfile:
        for line in brainfile:
            data = line.rstrip().split(',')
            # Unicodedata normalize NFKD: Map logically equiv chars (such as arabic inital, middle, and end forms, capital letters, japanese kana, etc.)
            add_to_brain(brain, data[0], unicodedata.normalize('NFKD', data[1]), data[2], data[3], False)
    return brain
def solicit_user_answer(question, options):
    print("Answer not known.")
    print("Question: %s" % question)
    print("Answers:")
    for i, opt in enumerate(options):
        print("%d) %s" % (i,opt))
    userans = -1
    while userans < 0 or userans >= len(options):
        try:
            userans = int(input("Enter the correct number: "))
        except ValueError:
            userans = -1
    print("You chose: %s" % options[userans])
    return options[userans]
def lookup_answer(brain, question):
    ans = None
    for line in brain:
        if line['p1'] == question:
            ans = line['p2']
        elif line['p2'] == question:
            ans = line['p1']
    return ans
def update_brain(brain):
    # TODO only append new stuff. Check if exists already before append to file
    print('Saving brain file.')
    # Save off the existing file, just in case
    d = datetime.datetime.today()
    timestamp = d.strftime("%Y%m%d_%H%M%S")
    newname = "brain-%s.bak.csv" % (timestamp)
    os.rename(BRAIN_FILE, newname)
    print('Existing brain backed up to: %s' % newname)
    # Output the contents of the in-memory brain to csv
    with open(BRAIN_FILE, 'w') as brainfile:
        for line in brain:
            brainfile.write("%s,%s,%s,%s\n" % (line['p1'], line['p2'], line['language'], line['lesson']))
def get_progress(driver):
    return driver.find_element_by_css_selector('._1TkZD').get_attribute('style').split()[-1][:-1] # Get last style (width), shave off the semicolon
def next_question(driver):
    driver.find_element_by_css_selector('button[data-test="player-next"]').click()
    time.sleep(SLEEP_NEXT_QUESTION)
def complete_multiple_choice(driver, brain, q, elem_a, language, lesson):
    # Search for match
    match = False
    n1 = unicodedata.normalize('NFKD', q)
    ans = lookup_answer(brain, n1)
    if ans == None:
        ans = solicit_user_answer(q, [x.text for x in elem_a])
        add_to_brain(brain, n1, ans, language, lesson)
    for elem in elem_a:
        if elem.text == ans:
            try:
                elem.click()
            except ElementClickInterceptedException:
                pass
            break
    # Submit answer
    driver.find_element_by_css_selector('button[data-test="player-next"]').click()
    # Continue to next question
    next_question(driver)
def complete_tapping(driver, brain, elem_tap, language, lesson):
    tapped = 0
    for elem1 in elem_tap:
        try:
            if elem1.is_enabled() == False or tapped >= len(elem_tap) // 2:
                continue
        except StaleElementReferenceException:
            break
        elem1_ans = lookup_answer(brain, elem1.text)
        if elem1_ans is None:
            elem1_ans = solicit_user_answer(elem1.text, [x.text for x in elem_tap])
            add_to_brain(brain, elem1.text, elem1_ans, language, lesson)
        elem1.click()
        for elem2 in elem_tap:
            if elem2.text == elem1_ans:
                elem2.click()
                tapped += 1
                break
    # Done tapping! :)
    next_question(driver)
def complete_write_in(driver, brain, prompt, language, lesson):
    q = driver.find_element_by_css_selector('span[data-test="hint-sentence"]').text
    ans = lookup_answer(brain, q)

    btn_difficulty = driver.find_elements_by_css_selector('button[data-test="player-toggle-keyboard"]')

    # If the answer is known, click "Make harder" and write it in
    if ans is not None:
        # Click "Make Harder" so we can just type the text in (if it exists)
        if len(btn_difficulty) and btn_difficulty[0] and btn_difficulty[0].text == "MAKE HARDER":
            btn_difficulty[0].click()
        elem_txt = driver.find_element_by_css_selector('textarea[data-test="challenge-translate-input"]')
        elem_txt.send_keys(ans)

    # Else, solicit user input for the correct word order OR just type it if it's their native language
    else:
        # Click "Make easier" so the user doesn't have to type anything but numbers
        print("Answer not known.")
        print("Question: %s" % q)

        is_native_language = prompt.split()[-1] == NATIVE_LANG

        if is_native_language:
            ans = input("Write the answer: ")
            elem_txt = driver.find_element_by_css_selector('textarea[data-test="challenge-translate-input"]')
            elem_txt.send_keys(ans)
            add_to_brain(brain, q, ans, language, lesson)
        else:
            if len(btn_difficulty) == 1 and btn_difficulty[0].text == "MAKE EASIER":
                btn_difficulty.click()
            choices = driver.find_elements_by_css_selector('button[data-test="challenge-tap-token"]')
            choices_txt = [x.text for x in choices]
            choices_txt.append('Done')
            current_answer = []
            while len(current_answer) < len(choices_txt):
                last_ans = solicit_user_answer(q, choices_txt)
                # Is user done?
                if last_ans == 'Done':
                    break
                current_answer.append(last_ans)
                print("Answer so far: %s" % current_answer)
                # Click the right one
                for elem in choices:
                    if elem.text == last_ans:
                        elem.click()
                        break

    # Either way, submit answer when done
    driver.find_element_by_css_selector('button[data-test="player-next"]').click()
    next_question(driver)
def add_to_brain(brain, phrase1, phrase2, language, lesson, update_brain_check=UPDATE_BRAIN):
    # print("Adding to brain: %s,%s,%s,%s" % (phrase1, phrase2, language, lesson))
    brain.append({'p1':phrase1,'p2':phrase2, 'language':language, 'lesson': lesson})
    if update_brain_check:
        update_brain(brain)
def autocomplete_skill(driver, brain, language, lesson):
    # Lesson title: Are we getting XP for this or what?
    learning_title = driver.find_element_by_css_selector('h2.nyHZG')
    print("Lesson title: %s" % learning_title.text)

    # Start lesson
    print("Starting lesson.")
    driver.find_element_by_css_selector('button[data-test="player-next"]').click()

    # For each question
    i = -1
    while True:
        i += 1
        progress = get_progress(driver)
        print("Progress: %s" % progress)
        # Wait 2 seconds if we're over 85% to prevent jumping the gun
        if int(progress[:-1]) > 85:
            time.sleep(2)
        # Sleep when finished
        if progress == "100%":
            time.sleep(2)
            break

        try:
            prompt = driver.find_element_by_css_selector('h1[data-test="challenge-header"] span').text
        except NoSuchElementException:
            # Most likely: Duo popped up and told us we're doing a nice job.
            prompt = None
            # Continue to next question
            next_question(driver)
            continue
        print("Prompt: %s" % prompt)

        if prompt == "What sound does this make?":
            q = driver.find_element_by_css_selector('span[dir="rtl"]').text
            elem_a = driver.find_elements_by_css_selector('div[data-test="challenge-judge-text"]')
            complete_multiple_choice(driver, brain, q, elem_a, language, lesson)
        elif prompt.startswith("Select the correct character(s) for"):
            q = prompt.split()[-1][1:-1] # get the last word, remove quotation marks
            elem_a = driver.find_elements_by_css_selector('label[data-test="challenge-choice-card"] div:first-child span[dir="rtl"]')
            complete_multiple_choice(driver, brain, q, elem_a, language, lesson)
        elif prompt == "Match the pairs":
            elem_tap = driver.find_elements_by_css_selector('button[data-test="challenge-tap-token"]')
            complete_tapping(driver, brain, elem_tap, language, lesson)
        elif prompt == "Mark the correct meaning":
            q = driver.find_element_by_css_selector('.KRKEd._3xka6').text
            elem_a = driver.find_elements_by_css_selector('div[data-test="challenge-judge-text"]')
            complete_multiple_choice(driver, brain, q, elem_a, language, lesson)
        elif prompt.startswith("Write this in"):
            complete_write_in(driver, brain, prompt, language, lesson)
        elif prompt == "Tap what you hear":
            # ain't nobody got time for that
            # Click skip
            driver.find_element_by_css_selector('button[data-test="player-skip"]').click()
            next_question(driver)
        else:
            print("Error - Unknown prompt type: %s" % prompt)
            sys.exit(1)
    # Acknowledge end of lesson
    driver.find_element_by_css_selector('button[data-test="player-next"]').click()
    # No thanks to plus
    driver.find_element_by_css_selector('button[data-test="no-thanks-to-plus"]').click()

def main():
    # Find out which language is currently being learned from dropdown
    lang_icon = driver.find_element_by_css_selector("._3gtu3._1-Eux.iDKFi")
    lang_icon.click()
    lang_name = driver.find_element_by_css_selector(".U_ned").text

    print("Currently learning: %s" % lang_name)
    if lang_name != "Arabic":
        print("Error: Currently only Arabic is supported.") #TODO
        sys.exit(1)

    # Find out which skills are listed
    print("Available skills:")
    skills = driver.find_elements_by_css_selector('div[data-test="skill"]')
    skill_buttons = [s.find_element_by_xpath("./div/div/div[position()=1]") for s in skills]
    skill_titles = [s.find_element_by_xpath("./div/div/div[position()=2]").text for s in skills]
    for s in skill_titles:
        print("%s, " % s, end='')
    print()

    skill_icons = driver.find_elements_by_xpath("//div[@data-test='skill-icon']")
    # Click lesson number 3 (0-based)
    for LANG_NUM in range(0,5):
        skill_icons[LANG_NUM].click()
        start_button = driver.find_element_by_xpath("//button[@data-test='start-button']")
        start_button.click()

        # Wait for skill to load
        time.sleep(2)

        autocomplete_skill(driver, brain, lang_name, skill_titles[LANG_NUM])


    driver.close()

class DuoBot:
    def __init__(self):
        self.driver = webdriver.Firefox()
        self.brain = build_brain()
        self.cfg = load_config()
        #
        self.driver.implicitly_wait(self.cfg['webdriver_wait'])
        #
        self.logged_in = False
        self.current_language = None
    def __del__(self):
        self.driver.close()
    def perform_login(self):
        """ Perform login to DuoLingo website
        Precondition: Not logged in
        Postcondition: Logged in, driver is at '/learn'
        Returns:
            True if successful login
            False if login failed
        """
        # Open up the page
        self.driver.get(URL)
        # Click "I already have an account"
        elem = self.driver.find_element_by_xpath("//a[text()[contains(.,'I ALREADY HAVE AN ACCOUNT')]]")
        elem.click()
        # Type the username
        elem = self.driver.find_element_by_xpath("//input[@placeholder='Email or username']")
        elem.send_keys(self.cfg['username'])
        # Type the password
        elem = self.driver.find_element_by_xpath("//input[@placeholder='Password']")
        elem.send_keys(self.cfg['password'])
        # Click login
        elem = self.driver.find_element_by_xpath("//button[@type='submit' and contains(text(),'Log in')]")
        elem.click()
        # Success: URL is correct
        # TODO add success check
        success = False
        try:
            page_header_text = self.driver.find_element_by_css_selector(CSS_CLASS_HEADER).text
            success = page_header_text == 'LEARN'
        except NoSuchElementException:
            success = False
        finally:
            return success
    def get_current_language(self):
        """ Get current language
        Precondition: Logged in, driver is at URL '/learn'
        Postcondition: self.current_language set to current language on Duo site
        Returns:
            True if successfully set current_language
            False if failed
        """
        if not self.driver.current_url.endswith('/learn'):
            return False

        # Find out which language is currently being learned from dropdown
        lang_name = None
        while lang_name is None:
            lang_icon = self.driver.find_element_by_css_selector(CSS_CLASS_LANG_ICON)
            lang_icon.click()
            try:
                lang_name = self.driver.find_element_by_css_selector(CSS_CLASS_LANG_NAME).text
            except NoSuchElementException:
                pass
            except StaleElementReferenceException:
                pass
            # Click the header to prevent hangups
            self.driver.find_element_by_css_selector(CSS_CLASS_HEADER)

        self.current_language = lang_name
        return True

if __name__ == "__main__":
    bot = DuoBot()
    success = bot.perform_login()
    print("Succeeded: %s" % success)
    bot.quit()