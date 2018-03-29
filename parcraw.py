import os
import requests
import argparse
import Nparser
import refiner
import re
from datetime import datetime
from lxml import etree

from timeout_deco import timeout


@timeout(3)
def request_get(url, root=''):
    sess = requests.Session()
    sess.headers[
        'User-Agent'] = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/34.0.1847.131 Safari/537.36'
    sess.headers['Referer'] = url

    try:
        req = sess.get(root + url)
    except:
        print('request_get() error!! Request was failed..')
        return False

    return req


@timeout(5)
def _get_etree(url, xpath, site_info):
    # page_list
    # [(url1, name1),
    #  (url2, name2),
    #  (url3, name3),
    #  ...
    #  ...]

    req = request_get(url)
    req.raise_for_status()
    req.encoding = None

    etr = etree.HTML(req.text)

    page_list = list()
    elm_list = etr.xpath(xpath)

    for elm in elm_list:
        # print(elm.text, elm.get('href'))
        subpage_url = elm.get('href')  # URL
        if not elm.text == None and re.search('[가-힣a-zA-Z]+', elm.text):
            subpage_name = elm.text
        else:
            subpage_name = subpage_url.split('/')[-1]
        # print(subpage_name)
        if subpage_url[:4] == 'http':
            page_list.append((subpage_url, subpage_name))

        elif not subpage_url[:4] == 'http' and site_info['NAME'] == 'daum':
            subpage_url = site_info['ROOT_URL'] + subpage_url.replace('/breakingnews', '')
            page_list.append((subpage_url, subpage_name))

        elif not subpage_url[:4] == 'http' and site_info['NAME'] == 'segye':
            subpage_url = site_info['ROOT_URL'].replace('/main', '') + subpage_url
            page_list.append((subpage_url, subpage_name))

        elif not subpage_url[:4] == 'http' and site_info['NAME'] == 'sbs':
            subpage_url = 'http://news.sbs.co.kr' + subpage_url
            page_list.append((subpage_url, subpage_name))

        elif not subpage_url[:4] == 'http' and site_info['NAME'] == 'hankyung':
            subpage_url = 'http://news.hankyung.com' + subpage_url
            page_list.append('http://news.hankyung.com' + subpage_url)

        elif not subpage_url[:4] == 'http' and not subpage_url[0] == '/' and site_info['NAME'] == 'herald':
            subpage_url = site_info['ROOT_URL'] + '/' + subpage_url
            page_list.append((subpage_url, subpage_name))

        else:
            subpage_url = site_info['ROOT_URL'] + subpage_url
            page_list.append((subpage_url, subpage_name))

    return page_list


@timeout(1)
def page(url, page_tag, numofpage):
    return url + (page_tag % numofpage)


@timeout(3)
def get_xml(url, filename, site_info, recent_file_list):
    # filename = site_info['NAME'] + url.split(site_info['PAGE_TAG'])[-1].replace('/', '_') + '.xml'
    if not filename in recent_file_list:
        put_recent_file_list(site_info, url, filename)

        req = request_get(url)

        if req == 0:
            return 0, 'Page Error'
        elif req.status_code == 404:
            print('Page "%s" get 404 ERROR!!!' % url)
            return 0, 'Page Error'

        req.raise_for_status()
        req.encoding = None

        if site_info['NAME'] == 'herald' or site_info['NAME'] == 'hani':
            req.encoding = 'ISO-639-1'

        with open(site_info['SAVE_PATH'] + filename, 'w') as f:
            f.write(req.text)
            print('%s (%s) was crawled!!' % (filename, url))

        return 1, site_info['SAVE_PATH'] + filename
    else:
        return 0, 'Already crawled'


@timeout(2)
def get_recent_file_list(site_information):
    # This function will list up all items in Source folder.
    # This list will be used for determining the crawled page already saved or not.
    file_name = site_information['NAME'] + '_list.txt'
    try:
        list_file = open(site_information['SAVE_PATH'] + file_name, 'r')
        print('File list of %s was loaded' % site_information['NAME'])
        file_list = list_file.read()
        file_info_list = file_list.split('\n')
        result = []
        for file_info in file_info_list:
            if file_info.find('\t') < 0:
                continue
            result.append(file_info.split('\t')[1])
        list_file.close()

        return file_list
    except:
        try:
            list_file = open(site_information['SAVE_PATH'] + file_name, 'w')
            print('File list of %s was maden' % site_information['NAME'])
            list_file.close()

            return []
        except:
            os.mkdir(site_information['SAVE_PATH'])
            list_file = open(site_information['SAVE_PATH'] + file_name, 'w')
            print('File list of %s was maden' % site_information['NAME'])
            list_file.close()

            return []


#    except FileExistsError:
#        list_file = open(site_information['SAVE_PATH'] + file_name, 'w')
#        print('File list of %s was maden' % site_information['NAME'])
#    except Exception as e:
#        print('get_recent_file_list() function error!')
#        print(e)


@timeout(2)
def put_recent_file_list(site_information, url, filename):
    list_file_name = '%s%s_list.txt' % (site_information['SAVE_PATH'], site_information['NAME'])
    with open(list_file_name, 'a') as f:
        f.write('%s\t%s\n' % (filename, url))


def parser_refiner(site_information, page_url, filename):
    parsed_text = Nparser.xml2txt(filename)
    parsed_filename = filename.replace('.xml', '_parsed.txt')
    Nparser.save(parsed_text, parsed_filename)

    # 크롤링 날짜
    now = datetime.now()
    date = now.strftime('%Y%m%d')

    refiner.normalize(parsed_filename, 'refined/' + site_information['NAME'] + '_%s_norm.txt' % date)


def crawler(site_information, max_page):
    # _get_etree() returns a list of tuples.
    # The tuple consists of (url, name)
    ### Example ###
    # boards_info = [(url1, name1), (url2, name2), (url3, name3), ... ]
    boards = _get_etree(site_information['ROOT_URL'], site_information['BOARD'], site_information)
    # 이전에 긁어왔던 페이지를 다시 긁어오지 않기 위한 변수
    r_file_list = get_recent_file_list(site_information)
    # 이번에 긁었던 페이지를 다시 긁지 않기 위한 변수
    crawled_posts = []
    # 크롤링 날짜
    now = datetime.now()
    date = now.strftime('%Y%m%d')

    numOfCrawledPosts = 0

    for board_info in boards:
        # board_info : (url, name)
        board_name = board_info[1]
        if board_name == None or board_name == '':
            board_name = '<UNK>'
        board_url = board_info[0]
        print('=' * 50)
        print(board_name, '(%s)' % board_url, 'Page crwaling starts.')

        nOfEmptyPostPages = 0

        for i in range(max_page):
            try:
                print('---------------', i + 1, 'th page...')

                # To check the number of empty or crawled pages
                nOfPost = 0

                # Open the page contains post list urls
                if site_information['NAME'] == 'donga':
                    page_url = page(board_url, site_information['PAGE_TAG'], 20 * i + 1)
                elif site_information['NAME'] == 'hani':
                    page_url = page(board_url.replace('home01.html', ''), site_information['PAGE_TAG'], i + 1)
                elif site_information['NAME'] == 'mlbpark':
                    page_url = page(board_url, site_information['PAGE_TAG'], 30 * i + 1)
                else:
                    page_url = page(board_url, site_information['PAGE_TAG'], i + 1)

                # Open page and Get post url list
                post_list = _get_etree(page_url, site_information['POST'], site_information)
                for post_info in post_list:
                    # post_info : (url, name) tuple object
                    post_url = post_info[0]
                    post_name = post_info[1]

                    # filename making
                    # SiteName_Date_BoardName_PageNum_PostNum.xml
                    filename = '%s_%s_%s_%04dP_%02d.xml' % (site_information['NAME'], date, board_name, i + 1, nOfPost + 1)

                    if post_url in crawled_posts:
                        print('*' * 50)
                        print("This post already crawled. We will skip this post.")
                        print('*' * 50)
                        continue
                    else:
                        try:
                            num, filepath = get_xml(post_url, filename, site_information, r_file_list)
                            crawled_posts.append(post_url)
                        except:
                            print('get_xml() ERROR!!')
                            continue

                    if filepath == 'Already crawled':
                        print('=' * 50)
                        print('This page already crawled. We will skip this page.')
                        print('=' * 50)
                        continue
                    elif filepath == 'Page Error':
                        print('=' * 50)
                        print('The page is not proper page. We will skip this page.')
                        print('=' * 50)

                    nOfPost += num

                    try:
                        parser_refiner(site_information, page_url, filepath)
                        nOfEmptyPostPages = 0
                    except Exception as e:
                        print('parser() ERROR!!!')
                        print(e)

                # If there is no new post in this page,
                # then we will skip this board. We already crawled all new post of this board.
                if nOfPost == 0:
                    print('There is no new post in this page. Or this page is not proper page.')
                    # If the nomber of this kind of pages over 100, then we will skip this board.
                    nOfEmptyPostPages += 1
                else:
                    numOfCrawledPosts += nOfPost

            except Exception as e:
                print('Post list page reading ERROR!!!')
                print(e)

            if nOfEmptyPostPages > 100:
                break

    print('#' * 50)
    print('Crwaling finishied!!')
    print('%d posts crawled.' % numOfCrawledPosts)
    print('#' * 50)

    return numOfCrawledPosts


def get_site_information_from_file():
    # FLAG parser settings
    parser = argparse.ArgumentParser()
    parser.add_argument('path', help='site infromation file (*.site) path', type=str)
    args = parser.parse_args()

    with open(os.getcwd() + '/' + args.path, 'r', encoding='utf-8') as f:
        l = f.readlines()

    site_information = {'NAME': args.path.split('/')[-1].replace('.txt', '')}

    for line in l:
        try:
            if line[0] == '#' or line == '\n':
                continue
            sep_idx = line.index('=')
            site_information[line[:sep_idx]] = line[sep_idx + 1:].replace('\n', '')
        except Exception as e:
            print('Getting site information ERROR!!!')

    return site_information


if __name__ == '__main__':
    site_information = get_site_information_from_file()

    # save_path = '/data/crawler/source/news/hani'
    crawler(site_information, 10000)
