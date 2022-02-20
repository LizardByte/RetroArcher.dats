import zipfile
from io import BytesIO
from time import sleep
import xml.etree.ElementTree as ElementTree
import re
import requests


# Config
url_home = 'http://redump.org/'
url_downloads = 'http://redump.org/downloads/'
regex = {
    'datfile': r'<a href="/datfile/(.*?)">',
    'date': r'\) \((.*?)\)\.',
    'name': r'filename="(.*?) Datfile',
    'filename': r'filename="(.*?)"',
}

xml_filename = 'redump.xml'


def _find_dats():
    download_page = requests.get(url_downloads)
    download_page.raise_for_status()

    dat_files = re.findall(regex['datfile'], download_page.text)
    return dat_files


def update_xml():
    dat_list = _find_dats()

    # zip file to store all DAT files
    zip_obj = zipfile.ZipFile(f'redump.zip', 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9)

    # clrmamepro XML file
    tag_clrmamepro = ElementTree.Element('clrmamepro')

    for dat in dat_list:
        print(f'Downloading {dat}')
        # section for this dat in the XML file
        tag_dat_file = ElementTree.SubElement(tag_clrmamepro, 'datfile')

        response = requests.get(url_home+'datfile/'+dat)
        content_header = response.headers['Content-Disposition']

        # XML version
        dat_date = re.findall(regex['date'], content_header)[0]
        ElementTree.SubElement(tag_dat_file, 'version').text = dat_date

        # XML name & description
        temp_name = re.findall(regex['name'], content_header)[0]
        # trim the - from the end (if exists)
        if temp_name.endswith('-'):
            temp_name = temp_name[:-2]
        elif temp_name.endswith('BIOS'):
            temp_name = temp_name + ' Images'
        ElementTree.SubElement(tag_dat_file, 'name').text = temp_name
        ElementTree.SubElement(tag_dat_file, 'description').text = temp_name

        # URL tag in XML
        ElementTree.SubElement(
            tag_dat_file, 'url'
        ).text = f'https://github.com/hugo19941994/auto-datfile-generator/releases/download/latest/redump.zip'

        # File tag in XML
        original_filename = re.findall(regex['filename'], content_header)[0]
        filename = f'{original_filename[:-4]}.dat'
        ElementTree.SubElement(tag_dat_file, 'file').text = filename

        # Author tag in XML
        ElementTree.SubElement(tag_dat_file, 'author').text = 'redump.org'

        # Command XML tag
        ElementTree.SubElement(tag_dat_file, 'comment').text = '_'

        # Get the DAT file
        dat_filename = f'{filename[:-4]}.dat'
        print(f'DAT filename: {dat_filename}')
        if original_filename.endswith('.zip'):
            # extract datfile from zip to store in the DB zip
            zip_data = BytesIO()
            zip_data.write(response.content)
            archive = zipfile.ZipFile(zip_data)
            zip_obj.writestr(dat_filename, archive.read(dat_filename))
        else:
            # add datfile to DB zip file
            dat_file = response.text
            zip_obj.writestr(dat_filename, dat_file)
        print()
        sleep(5)

    # store clrmamepro XML file
    xml_data = ElementTree.tostring(tag_clrmamepro).decode()
    xml_file = open(xml_filename, 'w')
    xml_file.write(xml_data)

    # Save DB zip file
    zip_obj.close()
    print('Finished')


try:
    update_xml()
except KeyboardInterrupt:
    pass
