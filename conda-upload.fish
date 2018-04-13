#!/usr/bin/fish

if [ x$CONDA_DEFAULT_ENV != x'pymoku-build' ]
    echo "Wrong Conda environment activated, $CONDA_DEFAULT_ENV, please activate pymoku-build"
    exit
end

anaconda login

for file in (find . -name 'pymoku-*.tar.bz2')
    echo "Uploading $file"
    anaconda upload $file
end

anaconda logout