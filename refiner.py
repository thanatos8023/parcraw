# -*- coding: utf-8 -*-

from timeout_deco import timeout
import re
import glob
import nltk
import CMUToKorean as ck
from korean import NumberWord, Loanword
import hanja

unit_ilist = ['kg', 'km', 'cm']
unit_rlist = ['킬로그램', '킬로미터', '센티미터']

arpabet = nltk.corpus.cmudict.dict()
c = ck.CMUToKorean

@timeout
def normalize(in_file, out_file):
    fin = open(in_file, 'rb')
    file_data = fin.read()
    try:
        file_data = file_data.decode('utf-8')
    except:
        file_data = file_data.decode('cp949')

    # 소설용: 마침표 기준으로 문장 분리
    # file_text = file_data.replace('\n', '')
    # file_text = file_text.split('.')

    # 일반용: \n 기준으로 문장 분리
    file_text = file_data.split('\n')

    try:
        fout = open(out_file, 'a', encoding='utf-8')
    except:
        fout = open(out_file, 'w', encoding='utf-8')

    word_cnt = 0
    line_cnt = 0
    only_word = {}
    for line in file_text:
        # 한 문장에서 영어가 50%를 넘어설 경우 문장을 분석하지 않음
        exp = re.compile('[a-zA-Z]+\s*')
        e_words = exp.findall(line.strip())
        e_len = 0

        if e_words:
            for e_word in exp.findall(line):
                e_len += len(e_word)

            if (e_len / len(line.strip())) > 0.5:
                continue

        # 불필요한 문장, 어절 제외
        line = text_except(line)

        # 고파스 댓글에 숫자다는 것 제거
        line = re.sub(u'^[0-9][0-9]/', u'', line)
        line = re.sub(u'^[0-9]/', u'', line)
        line = re.sub(u'ㅋ+', u'', line)

        # 기호 지우기 전에 문장분리?(.마침표) (2글자 이하(감탄사 추정) 제외..)
        # ' ' 혹은 " " 사이에 있는 마침표는 분리하지 않음
        if bool(re.search(u'.*(\.|\?|\!) ', line)) == True and len(re.search(u'.*(\.|\?|\!) ', line).group()) > 4:
            line = re.sub(u'(\.|\?|\!) ', u'\n', line)

        # 만약 한 문장이 10000 글자를 넘어갈 경우, 문장을 둘로 분리
        # while len(line) > 10000: 구현불가

        for oneline in line.split('\n'):
            # 숫자만 있으면 제외
            if oneline.isdigit() == True:
                continue

            # // 로 시작하면 제외 (주석)
            if oneline[:2] == '//':
                continue

            oneline = readUnit(oneline)  # 단위 읽기(%때문에 기호 제거 전에 처리)
            oneline = readNumber(oneline)  # 숫자 읽기
            oneline = re.sub(u'\(([0-9a-zA-Z가-힣一-龥豈-龎/]+\s*)+\)', u'', oneline)  # 괄호 안 부가 설명은 삭제

            # 숫자, 영어, 한글, 한문이 아니면 제외
            oneline = re.sub(u'[\'\"‘’“”]', u'', oneline)  # 따옴표 삭제
            oneline = re.sub(u'[^0-9a-zA-Z가-힣一-龥豈-龎]', u' ', oneline)  # 특수기호 제거
            oneline = longword_except(oneline)

            # 빈칸 처리
            oneline = re.sub(u' +', u' ', oneline)
            oneline = re.sub(u'^ ', u'', oneline)
            oneline = re.sub(u' $', u'', oneline)

            if bool(re.search('[一-龥豈-龎]', oneline)) == True:
                oneline = hanja.translate(oneline, 'substitution')  # 한자 읽기
            oneline = readAlphabet(oneline, 'ita')  # 영어 읽기

            # 빈칸 처리
            oneline = re.sub(u' +', u' ', oneline)
            oneline = re.sub(u'^ ', u'', oneline)
            oneline = re.sub(u' $', u'', oneline)

            if len(oneline) > 2000:
                print(oneline)
                continue
            if oneline != '' and oneline != ' ':
                word_cnt += len(oneline.split(' '))
                for my_word in oneline.split(' '):
                    only_word[my_word] = 0
                line_cnt += 1
                fout.write(oneline)
                fout.write('\n')

    fin.close()
    fout.close()

    print('word ' + str(word_cnt))
    print('line ' + str(line_cnt))
    print('only_word ' + str(len(only_word.keys())))


def text_except(line):
    line = re.sub(u'[＜<]img.*[＞>]', u' ', line)  # 이미지 링크
    line = re.sub(u'\w*@\w*\.+(com|ac\.kr|co\.kr|net|ge\.kr)+', u' ', line)  # 메일 주소
    line = re.sub(u'[ㄱ-ㅎㅏ-ㅣ]', u' ', line)  # 자음 모음
    line = re.sub(u'\[.+기자]', u' ', line)  # 머릿말
    line = re.sub(u'\[사진]\s*.*(기자|작가)', u' ', line)

    result = ''
    for word in line.split(' '):
        if bool(re.search(u'http://.+', word)) == True:
            word = re.sub(u'http://.+', u'', word)
        if word == '':
            continue
        if len(word) > 20:  # 한 어절이 20글자 이상이면 제외
            continue
        result += word
        result += ' '
    result = result[:-1]
    return result


def longword_except(line):
    result = ''
    for oneline in line.split('\n'):
        for word in oneline.split(' '):
            if len(word) > 20:  # 한 어절이 20글자 이상이면 제외
                continue
            result += word
            result += ' '
        result += '\n'
    result = result[:-1]
    return result


def readUnit(line):
    # g(그램),gb(기가바이트)...
    line = re.sub(u'%', u'퍼센트', line)

    for nunit in range(0, len(unit_ilist)):
        if bool(re.search('[^a-z]' + unit_ilist[nunit] + '[^a-z]', line)) == True:
            iter = re.search('[^a-z]' + unit_ilist[nunit] + '[^a-z]', line)
            ituple = iter.span()
            result = iter.group()[0] + unit_rlist[nunit] + iter.group()[-1]
            line = replaceSubstring(line, result, ituple)

    return line


def numToKor(num):
    num = re.sub(u'0', u'공', num)
    num = re.sub(u'1', u'일', num)
    num = re.sub(u'2', u'이', num)
    num = re.sub(u'3', u'삼', num)
    num = re.sub(u'4', u'사', num)
    num = re.sub(u'5', u'오', num)
    num = re.sub(u'6', u'육', num)
    num = re.sub(u'7', u'칠', num)
    num = re.sub(u'8', u'팔', num)
    num = re.sub(u'9', u'구', num)
    return num


def numToKor2(ch):
    return {
        '0': '',
        '1': '열',
        '2': '스물',
        '3': '서른',
        '4': '마흔',
        '5': '쉰',
        '6': '예순',
        '7': '일흔',
        '8': '여든',
        '9': '아흔',
    }.get(ch, ch)


def numToKor3(ch):
    return {
        '0': '',
        '1': '한',
        '2': '두',
        '3': '세',
        '３': '세',
        '4': '네',
        '5': '다섯',
        '6': '여섯',
        '7': '일곱',
        '8': '여덟',
        '9': '아홉',
    }.get(ch, ch)


def numsToChar(lch, rch):
    if lch == '2' and rch == '0':
        return '스무'

    result = numToKor2(lch)
    if rch != '0':
        result += ' '
        result += numToKor3(rch)
    else:
        result += numToKor3(rch)
    return result


def readNumber(line):
    # 문장에 숫자 없으면 리턴
    if bool(re.search('\d', line)) == False:
        return line

    # 전화번호 처리
    pnstr = '[0-9공일이삼사오육칠팔구]'
    while bool(re.search(u'\d{2,3}' + '[- ](' + pnstr + '{3,4})[- ]' + pnstr + '{4}', line)) == True:
        iter = re.search(u'\d{2,3}' + '[- ](' + pnstr + '{3,4})[- ]' + pnstr + '{4}', line)
        line = replaceSubstring(line, numToKor(iter.group()), iter.span())

    while bool(re.search(u'010' + pnstr + '{8}', line)) == True:
        iter = re.search(u'010' + pnstr + '{8}', line)
        line = replaceSubstring(line, numToKor(iter.group()), iter.span())

    # 년생 처리(빠른 96 -> 빠른 구육)
    while bool(re.search(u'빠른 ?\d\d\D', line)) == True:
        iter = re.search(u'빠른 ?\d\d\D', line)
        result = numToKor(iter.group()[:-3])
        result += numToKor(iter.group()[-3:-1])
        result += numToKor(iter.group()[-1])
        line = replaceSubstring(line, result, iter.span())

    # 학번 처리(96학번 -> 구육학번)
    while bool(re.search(u'\d\d(학번| 학번)', line)) == True:
        iter = re.search(u'\d\d(학번| 학번)', line)
        line = replaceSubstring(line, numToKor(iter.group()[:2]) + iter.group()[2:], iter.span())

    # 시간 처리(11시간 -> 열 한시간), 명 처리(11명 -> 열 한명), 개(개월x)?
    while bool(re.search(u'\d+(명|시)', line)) == True:
        iter = re.search(u'\d+(명|시)', line)
        numori = int(iter.group()[:-1])
        result = ''
        if numori >= 100:
            numint = int(numori / 100)
            numint = numint * 100
            result = NumberWord(numint).read()

        numint = numori % 100
        if numint == 20:
            result = '스무 '
        elif numint >= 10:
            numint = int(numint / 10)
            result += numToKor2(str(numint)) + ' '

        numint = numori % 10
        result += numToKor3(str(numint))
        result += iter.group()[-1]

        line = replaceSubstring(line, result, iter.span())

    # 숫자 콤마 숫자 처리
    if bool(re.search(',', line)) == True:
        for i in range(1, 5):
            if bool(re.search('(^|\D)\d{1,3}(,\d{3}){' + str(5 - i) + '}', line)) == True:
                iter = re.search('\d{1,3}(,\d{3}){' + str(5 - i) + '}', line)
                line = replaceSubstring(line, NumberWord(int(re.sub(u',', '', iter.group()))).read(), iter.span())

    # 실수형
    while bool(re.search(u'\d+\.\d+', line)) == True:
        oriiter = re.search(u'\d+\.\d+', line)
        oristr = oriiter.group()
        intiter = re.search(u'\d+\.', oristr)
        intstr = NumberWord(int(intiter.group()[:-1])).read()
        floatiter = re.search(u'\.\d+', oristr)
        floatstr = re.sub(u'0', u'영', floatiter.group()[1:])
        floatstr = numToKor(floatstr)
        line = replaceSubstring(line, intstr + '점' + floatstr, oriiter.span())

    # 정수형
    while bool(re.search(u'\d+', line)) == True:
        iter = re.search(u'\d+', line)
        line = replaceSubstring(line, NumberWord(int(iter.group())).read(), iter.span())

    return line


def charToKor(ABC):
    ABC = re.sub(u'A', u'에이', ABC)
    ABC = re.sub(u'B', u'비', ABC)
    ABC = re.sub(u'C', u'씨', ABC)
    ABC = re.sub(u'D', u'디', ABC)
    ABC = re.sub(u'E', u'이', ABC)
    ABC = re.sub(u'F', u'에프', ABC)
    ABC = re.sub(u'G', u'지', ABC)
    ABC = re.sub(u'H', u'에이치', ABC)
    ABC = re.sub(u'I', u'아이', ABC)
    ABC = re.sub(u'J', u'제이', ABC)
    ABC = re.sub(u'K', u'케이', ABC)
    ABC = re.sub(u'L', u'엘', ABC)
    ABC = re.sub(u'M', u'엠', ABC)
    ABC = re.sub(u'N', u'엔', ABC)
    ABC = re.sub(u'O', u'오', ABC)
    ABC = re.sub(u'P', u'피', ABC)
    ABC = re.sub(u'Q', u'큐', ABC)
    ABC = re.sub(u'R', u'알', ABC)
    ABC = re.sub(u'S', u'에스', ABC)
    ABC = re.sub(u'T', u'티', ABC)
    ABC = re.sub(u'U', u'유', ABC)
    ABC = re.sub(u'V', u'브이', ABC)
    ABC = re.sub(u'W', u'더블유', ABC)
    ABC = re.sub(u'X', u'엑스', ABC)
    ABC = re.sub(u'Y', u'와이', ABC)
    ABC = re.sub(u'Z', u'지', ABC)
    return ABC


def readAlphabetByCMU(word):
    po = ''
    for a in arpabet[word][0]:
        po += a + ' '

    ko_word = c.convert(word, po)
    word = ko_word[0]
    return word


def readAlphabet(line, lang):
    if bool(re.search('[a-zA-Z]', line)) == False:
        return line

    while bool(re.search(u'[A-Z][A-Z]+', line)) == True:
        iter = re.search(u'[A-Z][A-Z]+', line)
        line = replaceSubstring(line, charToKor(iter.group()), iter.span())

    while bool(re.search(u'[a-zA-Z]+', line)) == True:
        iter = re.search(u'[a-zA-Z]+', line)
        str = iter.group()
        if str.isupper() == True:
            str = charToKor(str)
        else:
            try:
                str = readAlphabetByCMU(str.lower())
            except:
                str = Loanword(str, lang).read()
        line = replaceSubstring(line, str, iter.span())

    return line


def replaceSubstring(line, newstr, ituple):
    output = line[0:ituple[0]] + newstr + line[ituple[1]:]
    return output


if __name__ == '__main__':

    filelist = glob.glob('re_sample.txt')

    for filename in filelist:
        try:
            normalize(filename, 'refined_data/donga_norm.txt')
        except:
            continue
