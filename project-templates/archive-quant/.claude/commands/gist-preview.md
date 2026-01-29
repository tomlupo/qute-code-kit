Create a GitHub gist from the specified HTML file and return a preview link.

1. Run `gh gist create $ARGUMENTS --public` and capture the output URL
2. The output URL format is: https://gist.github.com/USERNAME/GIST_ID
3. Extract USERNAME and GIST_ID from this URL
4. Get the filename from $ARGUMENTS
5. Construct and return the preview link:
   https://htmlpreview.github.io/?https://gist.githubusercontent.com/USERNAME/GIST_ID/raw/FILENAME

Return only the clickable preview link.