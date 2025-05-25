#!/bin/sh
#Sample script to illustrate the automated GitBook changelog
#document creation process.  Not intended for production.

export TVH_DIR=/home/dmc/development/python/ListPRs/localrepo
export DOC_DIR=/home/dmc/development/python/ListPRs/docrepo
export TVH_MD=/home/dmc/development/python/ListPRs/changelog.md
export TVH_JSON=/home/dmc/development/python/ListPRs/localcache.json
export DOC_MD=/introduction/release-change-log.md

#Note: This script requires access to the TVH and GitBook repository.
#      If the build environment does not already have clones of these
#      repositories, they will need to be created before running this script.

#Refresh the local TVH GitHub repository
#git --git-dir $TVH_DIR/.git --work-tree $DOC_DIR pull

#Generate the changelog document for GitBook
#specifying the output file name and the location of the TVH repository.
python create_changelog.py -o $TVH_MD -g $TVH_DIR #-j $TVH_JSON -J $TVH_JSON
export TVH_STATUS=$?

#echo Got: "${TVH_STATUS}"

#If the return code is zero, all went well.
#The output file still could be send to GitBook if there is an error,
#however, the document will contain a section detailing the error(s) encountered.
if [ $TVH_STATUS = 0 ]; then
   echo "Changelog built OK.  Copying to GitBook."
   #Copy the new changelog document into the GitBook document repository.
   #cp $TVH_MD $DOC_DIR$DOC_MD
   #Add the updated changelog document to the commit.
   #git --git-dir $DOC_DIR/.git --work-tree $DOC_DIR add $DOC_DIR$DOC_MD
   #Commit the change.
   #git --git-dir $DOC_DIR/.git --work-tree $DOC_DIR commit -m "Automated update of GitBook changelog."
   #Push the change to github.
   #git --git-dir $DOC_DIR/.git --work-tree $DOC_DIR push
else
   echo "Changelog built with errors.  Sound the alarm!" ${TVH_STATUS}
fi
