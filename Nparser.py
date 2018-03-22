from bs4 import BeautifulSoup

import parcraw

import os
import glob


def get_txt(xml_file_object):
    source = xml_file_object.read()

    soup = BeautifulSoup(source, 'lxml')

    site_info = parcraw.get_site_information_from_file()

    title = soup.select(site_info['TITLE'])
    body = soup.select(site_info['BODY'])
    replys = soup.select(site_info['REPLY'])

    text = ''
    for elm in title:
        text += elm.text
    for elm in body:
        text += elm.text
    for elm in replys:
        text += elm.text

    while text.find('\n\n') >= 0:
        text = text.replace('\n\n', '\n')

    #print(text)

    return text


def xml2txt(path):
    #text = url + '\n\n'
    text = ''
    if os.path.isdir(path):
        filelist = glob.glob(path + "/*")

        for filename in filelist:
            with open(filename, 'r') as f:
                text += get_txt(f)
            os.remove(filename)
    else:
        with open(path, 'r') as f:
            text = get_txt(f)
        os.remove(path)

    return text


def save(text, path):
    with open(path, 'w') as f:
        f.write(text)


def main():
    file_list = glob.glob('source/naver*')

    for filename in file_list:
        text = xml2txt(filename)
        save(text, filename.replace('.xml', '_parsed.txt'))


if __name__ == '__main__':
    main()