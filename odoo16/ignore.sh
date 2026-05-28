git config --global core.excludesfile ignore.txt
find . -name "*.pyc" -exec rm -f {} \;
find . -path "*/__pycache__" -type d -exec rm -r {} ';'
