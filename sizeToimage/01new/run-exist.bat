@echo off
chcp 65001 > nul
python sizetoimageallnew.py PATAGONIA官网总表.xlsx PATAGONIA --skip-existing
pause
