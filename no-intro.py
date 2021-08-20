from time import sleep
from selenium import webdriver
import os
import re
import xml.etree.ElementTree as ET
import zipfile

regex = {
    'date': r'[0-9]{8}-[0-9]*',
    'name': r'(.*?.)( \([0-9]{8}-[0-9]*\).dat)',
    'filename': r'filename="(.*?)"',
}
xml_filename = 'no-intro.xml'

no_intro_type = {
    'standard': 1,
    'parent-clone': 2
}

# Dowload no-intro pack using selenium
dir_path = os.path.dirname(os.path.realpath(__file__))
fx_profile = webdriver.FirefoxProfile();
fx_profile.set_preference("browser.download.folderList", 2);
fx_profile.set_preference("browser.download.manager.showWhenStarting", False);
fx_profile.set_preference("browser.download.dir", dir_path);
fx_profile.set_preference("browser.helperApps.neverAsk.saveToDisk", "application/zip");

options = webdriver.FirefoxOptions()
options.headless = True

for key, value in no_intro_type.items():
    driver = webdriver.Firefox(firefox_profile=fx_profile, options=options);
    driver.implicitly_wait(10)

    driver.get("https://datomatic.no-intro.org")
    driver.find_element_by_xpath('/html/body/div/header/nav/ul/li[3]/a').click()
    driver.find_element_by_xpath('/html/body/div/section/article/table[1]/tbody/tr/td/a[6]').click()
    driver.find_element_by_xpath(f'/html/body/div/section/article/div/form/input[{value}]').click()
    driver.find_element_by_xpath('/html/body/div/section/article/div/form/input').click()

    # wait until file is found
    found = False
    name = None
    time_slept = 0
    while not found:
        if time_slept > 360:
            raise Exception(f'No-Intro {key} zip file not found')

        for f in os.listdir(dir_path):
            if 'No-Intro Love Pack' in f:
                name = f
                found = True
                break

        # wait 5 seconds
        sleep(5)
        time_slept += 5

    archive_name = f'no-intro ({key}).zip'
    archive_full = f'{dir_path}/{archive_name}'
    os.rename(name, archive_full)

    # load zip file
    archive = zipfile.ZipFile(archive_full)

    # clrmamepro XML file
    tag_clrmamepro = ET.Element('clrmamepro')
    for dat in archive.namelist():
        print(dat)
        # section for this dat in the XML file
        tag_datfile = ET.SubElement(tag_clrmamepro, 'datfile')

        # XML version
        dat_date = re.findall(regex['date'], dat)[0]
        ET.SubElement(tag_datfile, 'version').text = dat_date
        print(dat_date)

        # XML name & description
        tempName = re.findall(regex['name'], dat)[0][0]
        ET.SubElement(tag_datfile, 'name').text = tempName
        ET.SubElement(tag_datfile, 'description').text = tempName
        print(tempName)

        # URL tag in XML
        ET.SubElement(
            tag_datfile, 'url').text = f'https://github.com/retroarcher-resarch/dats/releases/download/latest/{archive_name}'

        # File tag in XML
        fileName = dat
        fileName = f'{fileName[:-4]}.dat'
        ET.SubElement(tag_datfile, 'file').text = fileName
        print(fileName)

        # Author tag in XML
        ET.SubElement(tag_datfile, 'author').text = 'no-intro.org'

        # Command XML tag
        ET.SubElement(tag_datfile, 'comment').text = '_'

    # store clrmamepro XML file
    xmldata = ET.tostring(tag_clrmamepro).decode()
    xmlfile = open(xml_filename, 'w')
    xmlfile.write(xmldata)
