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

    # Touch new html doc with jekyll front matter
    echo -e "---\nlayout: default\n---\n" > $new_path

    # Convert to html and add to html file
    jupyter nbconvert $nb --to html --stdout >> $new_path

    # Update the relative path links to assets directory
    sed -i '' -e 's&../docs/assets/&assets/&g' $new_path

done

# Add favicon to head of index file
fav='<link rel="icon" href="favicon.ico" type="image/x-icon">'
index='../docs/index.html'
awk -v var="$fav" '/<head>/ { print; print var; next }1' $index > tmp && mv tmp $index