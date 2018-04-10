#!/bin/bash

python parcraw.py site_info/chosun.txt > log/chosun_$(date +%Y%m%d).log &
python parcraw.py site_info/donga.txt > log/donga_$(date +%Y%m%d).log &
python parcraw.py site_info/khan.txt > log/khan_$(date +%Y%m%d).log &

echo "$(date)	크롤러가 실행되었습니다."
