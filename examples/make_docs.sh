path=../docs/
for nb in *.ipynb
do
    # Get length of upper and lower ### set
    N=$((${#nb}+25))
    head -c $N < /dev/zero | tr '\0' '#'
    echo
    echo "###### Processing $nb ######"
    head -c $N < /dev/zero | tr '\0' '#'
    echo

    # Get the basename
    base="${nb%.*}"
    
    # Specify output
    new_path="$path$base.html"

    # Rerun notebook
    jupyter nbconvert --to notebook --execute --clear-output --inplace $nb

    # Convert to html
    jupyter nbconvert $nb --to html --output $new_path

done