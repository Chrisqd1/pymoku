#!/usr/bin/fish

if [ "$CONDA_DEFAULT_ENV" != 'pymoku-build' ]
    echo "Wrong Conda environment activated, $CONDA_DEFAULT_ENV, please activate pymoku-build"
    exit
end

mkdir -p output
rm -r output/*

for ver in 2.7 3.4 3.5 3.6
    set output_file (conda build --python $ver pymoku | grep 'anaconda upload' | cut -d ' ' -f 3)
    conda convert --platform all $output_file -o output
end