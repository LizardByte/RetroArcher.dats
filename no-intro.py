from PIL import Image
from colormath.color_conversions import convert_color
from colormath.color_diff import delta_e_cie1976
from colormath.color_objects import LabColor, sRGBColor
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import NoSuchElementException
from time import sleep
import os
import re
import requests
import xml.etree.ElementTree as ElementTree
import zipfile

regex = {
    'date': r'[0-9]{8}-[0-9]*',
    'name': r'(.*?.)( \([0-9]{8}-[0-9]*\).dat)',
    'filename': r'filename="(.*?)"',
}

no_intro_type = {
    'standard': 'standard',
    'parent-clone': 'xml'
}


def color_lab(image_url: str):
    # download the captcha image
    image = Image.open(requests.get(image_url, stream=True).raw).convert('RGB')

    # Resize to get average color
    image = image.resize((1, 1))
    color = image.getpixel((0, 0))

    # Instantiate an sRGBColor object and convert to lab to check deltas
    rgb = sRGBColor(rgb_r=color[0], rgb_g=color[1], rgb_b=color[2], is_upscaled=True)
    lab = convert_color(rgb, LabColor)

    return lab


for key, value in no_intro_type.items():
    # Dowload no-intro pack using selenium
    dir_path = os.path.dirname(os.path.realpath(__file__))
    options = Options()
    options.set_preference("browser.download.folderList", 2)
    options.set_preference("browser.download.manager.showWhenStarting", False)
    options.set_preference("browser.download.dir", dir_path)
    options.set_preference("browser.helperApps.neverAsk.saveToDisk", "application/zip")
    options.headless = True

    service = Service()

    driver = webdriver.Firefox(service=service, options=options)
    driver.implicitly_wait(10)

    driver.get("https://datomatic.no-intro.org")

    # select downloads
    driver.find_element(by='xpath', value='/html/body/div/header/nav/ul/li[3]/a').click()

    # select daily downloads
    driver.find_element(by='xpath', value='/html/body/div/section/article/table[1]/tbody/tr/td/a[6]').click()

    # find the type of dat file
    x = driver.find_element(by='name', value='dat_type')
    drop = Select(x)

    # Select by value
    drop.select_by_value(value)
    sleep(5)

    # click the prepare button
    driver.find_element(by='xpath', value=f'/html/body/div/section/article/div/form/input[1]').click()

    try:
        captcha_image = driver.find_element(
            by='xpath', value='/html/body/div/section/article/div/form/img').get_attribute('src')
    except NoSuchElementException:
        pass
        buttons = driver.find_elements(
            by='xpath', value="/html/body/div/section/article/div/form/input[@type='submit']")
        if len(buttons) == 1:
            btn_name = buttons[0].get_attribute('name')
            driver.find_element(by='name', value=btn_name).click()
    else:
        captcha_lab = color_lab(image_url=captcha_image)

        # Get colors from the buttons
        buttons_dict = {}
        buttons = driver.find_elements(
            by='xpath', value="/html/body/div/section/article/div/form/input[@type='submit']")
        for btn in buttons:
            btn_css = btn.value_of_css_property("background")
            btn_url = re.search(r'url\("(.*)"\)', btn_css).group(1)
            btn_url = f'https://datomatic.no-intro.org/{btn_url}'

            btn_lab = color_lab(image_url=btn_url)

            # get difference of color between button and captcha_image
            delta_e = delta_e_cie1976(btn_lab, captcha_lab)

            buttons_dict[btn.get_attribute('name')] = delta_e
        closest_button_name = min(buttons_dict, key=buttons_dict.get)

        # click the correct captcha color coded download button
        driver.find_element(by='name', value=closest_button_name).click()

    # wait until file is found
    found = False
    name = None
    time_slept = 0
    while not found:
        if time_slept > 360:
            raise Exception(f'No-Intro {key} zip file not found')

        for f in os.listdir(dir_path):
            if 'No-Intro Love Pack' in f and not f.endswith('.part'):
                try:
                    zipfile.ZipFile(os.path.join(dir_path, f))
                    name = f
                    found = True
                    break
                except zipfile.BadZipfile:
                    pass

        # wait 5 seconds
        sleep(5)
        time_slept += 5

    archive_name = f'no-intro_{key}.zip'
    archive_full = os.path.join(dir_path, archive_name)
    os.rename(os.path.join(dir_path, name), os.path.join(dir_path, archive_full))

    # load zip file
    archive = zipfile.ZipFile(os.path.join(dir_path, archive_full))

    # clrmamepro XML file
    tag_clrmamepro = ElementTree.Element('clrmamepro')
    for dat in archive.namelist():
        if dat.find('(') >= 0 or dat.find(')') >= 0:
            print(dat)
            # section for this dat in the XML file
            tag_datfile = ElementTree.SubElement(tag_clrmamepro, 'datfile')

            # XML version
            dat_date = re.findall(regex['date'], dat)[0]
            ElementTree.SubElement(tag_datfile, 'version').text = dat_date
            print(dat_date)

            # XML name & description
            tempName = re.findall(regex['name'], dat)[0][0]
            ElementTree.SubElement(tag_datfile, 'name').text = tempName
            ElementTree.SubElement(tag_datfile, 'description').text = tempName
            print(tempName)

            # URL tag in XML
            ElementTree.SubElement(
                tag_datfile,
                'url').text = f'https://github.com/retroarcher-resarch/dats/releases/download/latest/{archive_name}'

            # File tag in XML
            fileName = dat
            fileName = f'{fileName[:-4]}.dat'
            ElementTree.SubElement(tag_datfile, 'file').text = fileName
            print(fileName)

            # Author tag in XML
            ElementTree.SubElement(tag_datfile, 'author').text = 'no-intro.org'

            # Command XML tag
            ElementTree.SubElement(tag_datfile, 'comment').text = '_'

    # store clrmamepro XML file
    xml_data = ElementTree.tostring(tag_clrmamepro).decode()
    xml_filename = f'no-intro_{key}.xml'
    xml_file = open(xml_filename, 'w')
    xml_file.write(xml_data)
