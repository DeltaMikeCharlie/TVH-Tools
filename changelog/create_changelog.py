
'''

*** Script to generate release notes in markdown format for GitBook ***

* Extract commits from the TVH GitHub repository.
* Extract releases from the Cloudsmith site.
* Sort them together by descending date, prioritising the Coudsmith records so that they sort before the commits.
* Produce a MD document that can be pushed to the TVH documentation repository.
* Various MD document sections can be skipped by setting command line arguements.
* The results can be dumped to JSON by setting a command line arguement.

usage: create_changelog.py [-h] [-g GITHUB_REPO] [-o OUTPUT_FILE] [-j OUTPUT_JSON] [-J INPUT_JSON] [-i] [-l] [-r] [-c]

options:
  -h, --help            show this help message and exit
  -g GITHUB_REPO, --github-repo GITHUB_REPO
                        Location of the TVH GitHub repository.
  -o OUTPUT_FILE, --output-file OUTPUT_FILE
                        Name of the output markdown file.
  -j OUTPUT_JSON, --output-json OUTPUT_JSON
                        If present, dump the results into the specified JSON file.
  -J INPUT_JSON, --input-json INPUT_JSON
                        If present, load the specified JSON file and produce the markdown file from that.
  -i, --ignore-new      Only use data from the saved JSON file, do not query external sources.
  -l, --skip-latest     Do not output the 'Latest Release' section.
  -r, --skip-recent     Do not output the 'Recent Releases' section.
  -c, --skip-changelog  Do not output the 'Releases, Nightly Builds and Change Log' section.


The script sets a non-zero return code if errors encountered.
A return code of zero means that no errors were encountered.

DeltaMikeCharlie - August 2024

'''

#Some useful URLs and commands discovered during development
#git log --date=format:'%Y-%m-%d %H:%M:%S' --pretty=fuller
#git --git-dir /home/dmc/development/TVH/xpath/tvheadend/.git log --date=format:'%Y-%m-%d %H:%M:%S' --pretty=fuller
#https://github.com/gitpython-developers/GitPython
#https://github.com/ishepard/pydriller
#https://cloudsmith.io/~cloudsmith/repos/cli/packages/

#https://api.github.com/repos/tvheadend/tvheadend/pulls?state=all&sort=updated&per_page=100&page=1
#https://api.github.com/repos/tvheadend/tvheadend/commits?per_page=100&page=1&since=2018-10-16
#https://api.cloudsmith.io/v1/packages/owner/repo/?sort=-date
#https://api.cloudsmith.io/v1/packages/tvheadend/tvheadend/?sort=-date&page_size=100
#https://api.cloudsmith.io/v1/packages/tvheadend/tvheadend/?sort=-date&page_size=100&page=3
#https://api.cloudsmith.io/v1/packages/tvheadend/tvheadend/?sort=-date&page_size=100&q=architecture:amd64
#https://api.cloudsmith.io/v1/packages/tvheadend/tvheadend/?query=uploaded:%272024-08-11%27
#The API can accept filter parameters.
#https://api.cloudsmith.io/v1/packages/tvheadend/tvheadend/?query=uploaded:%3E=%272024-07-12%27&page_size=1000
#https://api.cloudsmith.io/v1/packages/tvheadend/tvheadend/?query=uploaded:%3E=%272024-07-12%27%20AND%20architecture:amd64&page_size=1000

#https://cloudsmith.io/~tvheadend/repos/tvheadend/packages/?q=version%3A4.3-2351~g078a822~xenial
#https://cloudsmith.io/~tvheadend/repos/tvheadend/packages/?q=version%3A4.3-2351*

import os.path					#Needed for file caching functionality during development.
import json					#Needed to decode the JSON returned by the API calls.
import datetime					#Needed for the date/time stamp and UTC conversion.
from urllib.request import urlopen		#Needed to call the remote APIs.
from urllib.error import URLError, HTTPError	#Needed for URL error trapping.
import sys					#Needed to provide an exit code on error.
import argparse					#Needed for processing command line arguements.
from pydriller import Repository		#Needed for GitHub repository access. From: https://github.com/ishepard/pydriller

#Global variables
OUTPUT_FILE = "changelog.md"			#Markdown file name.
OUTPUT_JSON = ""				#JSON dump file name.
INPUT_JSON = ""					#JSON dump file name to use as input instead of the repositories.
GITHUB_REPO = "https://github.com/tvheadend/tvheadend" #The location of the GitHub repository to query. Local is quicker, but remote will work.
#GITHUB_REPO = "/home/dmc/development/python/ListPRs/localrepo"
PERPAGE = 100					#Records per page to request.
USE_LOCAL_CACHE = True  			#For external API sources.  Should be set to False so that the production run always uses live data.
FIRSTDATE = datetime.datetime(2018,10,16,0,0,0)	#Ignore records before this date.  
FIRSTDATE_TEXT = FIRSTDATE.strftime('%Y-%m-%d') #Ignore records before this date.
RESULTS = []					#This holds a mixture of GitHub commits and Cloudsmith versions, sorted by date.
INTL_NAMES = ["transifex-integration[bot]"]	#List of author names that should be handled as translators.
ANNOTATIONS = []				#This holds the multi-line commit messages for the tooltip annotation.
VERSIONS = []					#This holds the unique version numbers found on Cloudsmith.
ERRORS = []					#This holds the errors encountered when fetching remote API data, etc.
RUN_NOTES = []					#This hold the parameters used for this run.  Used as an annotation on the datestamp.
RELEASECOUNT = 0				#Track how many 'releases' are encountered.
ANNCOUNT = 1					#Annotations start at 1.
SKIP_LATEST = False				#If true, do not output the 'Latest Release' section.
SKIP_RECENT = False				#If true, do not output the 'Recent Releases' section.
SKIP_CHANGELOG = False				#If true, do not output the 'Releases, Nightly Builds and Change Log' section.
IGNORE_NEW = False				#If true, do not go to external sources, only use the stored JSON file.

#Build the URL for the Cloudsmith search
#TODO - This may change when 'releases' are implemented.
def cloudsmithURL(release):
	if 'version' in release:
		return "https://cloudsmith.io/~tvheadend/repos/tvheadend/packages/?q=version%3A" + release['version'] + "*"
	else:
		return ""

#Get the requested page from the requested source or local cache.
def getPage(pageNum, prefix):
	fileName = prefix + "-" + str(PERPAGE) + "-" + str(pageNum) + ".json"
	#print("Getting Page", pageNum, fileName)
	gotData = False
	if USE_LOCAL_CACHE:
		if os.path.isfile(fileName):
			#print("File exists")
			with open(fileName) as JSONfile:
				gotData = True
				return json.load(JSONfile)
	if not gotData:
		if prefix == "GH":
			pageURL = "https://api.github.com/repos/tvheadend/tvheadend/commits?per_page=" + str(PERPAGE) + "&page=" + str(pageNum) + "&since=" + FIRSTDATE_TEXT
		if prefix == "CS":
			#This request only gets AMD64 releases to reduce the volume of entries returned.
			pageURL = "https://api.cloudsmith.io/v1/packages/tvheadend/tvheadend/?sort=-date&q=architecture:amd64&page_size=" + str(PERPAGE) + "&page=" + str(pageNum)

		#print(pageURL)
		#Note: Error trapping has been tested with invalid URLs only.
		#      Network time-outs, etc, may not be trapped properly.
		pageData = ""
		try:
			response = urlopen(pageURL)
		except HTTPError as err:
			ERRORS.append("HTTP error '" + str(err.code) + "' fetching URL '" + pageURL + "'")
		except URLError as err:
			ERRORS.append("URL error '" + str(err.reason) + "' fetching URL '" + pageURL + "'")
		else:
			pageData = response.read()
			gotData = True

		#If we are using local caching (dev only), save the data that just arrived.
		if USE_LOCAL_CACHE:
			localCache = open(fileName, "wb")
			localCache.write(pageData)
			localCache.close

		if gotData:
			return json.loads(pageData)
		else:
			return b''

#Write the body of the document.
#If 'latestMode' is true, then we are only producing output for the most recent release.
#TODO - Maybe add releaseStart/releaseLimit parameters to allow for the 'recent releases' to be processed with this function too.
def outputBody(output, latestMode):
	global ANNCOUNT
	produceOutput = True	#This controls when lines are to be written or not.
	#Only wait for a release if latestMode is true.
	if latestMode == True:
		produceOutput = False
	for result in RESULTS:
		#output.write(str(produceOutput) + " " + str(result) + "\n")  #Uncomment this line to output whole object into the MD file for debugging
		#A release will contain a 'release' property
		#Wait for the first release before outputting
		#and only output until the next release is reached.
		if 'release' in result and latestMode:
			if produceOutput == True:
				break
			else:
				produceOutput = True
		
		#Commits contain a 'text' property, Cloudsmith releases to not.
		if 'text' in result and produceOutput:
			#If the commit text contains multiple lines, attach an annotation.
			if len(result['text']) > 1:
				outputText = "* [" + result['text'][0] + "](#user-content-fn-" + str(ANNCOUNT) + ")[^" + str(ANNCOUNT) + "]"
				annObj = {}
				annObj['index'] = ANNCOUNT
				annObj['lines'] = result['text']
				ANNOTATIONS.append(annObj)
				ANNCOUNT = ANNCOUNT + 1
			else:
				outputText = "* " + result['text'][0]
			output.write(outputText + " ([" + result['date'] + "]" + "(" + result['url']  + "))" + "\n\n")
		else:
		#This is a Cloudsmith release line.
			if not latestMode:
				if 'release' in result:
					output.write("* [Release " + result['release'] + "](" + cloudsmithURL(result) + ") (" + result['date'] + ")\n\n")
				else:
					output.write("* [Nightly build " + result['version'] + "](" + cloudsmithURL(result) + ") (" + result['date'] + ")\n\n")
			else:
				if 'release' in result:
					output.write("## [Latest Release " + result['release'] + "](" + cloudsmithURL(result) + ") (" + result['date'] + ")\n\n")

##### MAIN SCRIPT STARTS HERE #####

#Process the command line arguements.
parser = argparse.ArgumentParser()
parser.add_argument('-g','--github-repo', help='Location of the TVH GitHub repository.')
parser.add_argument('-o','--output-file', help='Name of the output markdown file.')
parser.add_argument('-j','--output-json', help='If present, dump the results into the specified JSON file.')
parser.add_argument('-J','--input-json', help='If present, load the specified JSON file and produce the markdown file from that.')
parser.add_argument('-i','--ignore-new', help='Only use data from the saved JSON file, do not query external sources.', action="store_true")
parser.add_argument('-l','--skip-latest', help='Do not output the \'Latest Release\' section.', action="store_true")
parser.add_argument('-r','--skip-recent', help='Do not output the \'Recent Releases\' section.', action="store_true")
parser.add_argument('-c','--skip-changelog', help='Do not output the \'Releases, Nightly Builds and Change Log\' section.', action="store_true")
args = vars(parser.parse_args())
#print(args)

if args['github_repo'] is not None:
	GITHUB_REPO = args['github_repo']

if args['output_file'] is not None:
	OUTPUT_FILE = args['output_file']

if args['output_json'] is not None:
	OUTPUT_JSON = args['output_json']

if args['input_json'] is not None:
	INPUT_JSON = args['input_json']
	
SKIP_LATEST = args['skip_latest']
SKIP_RECENT = args['skip_recent']
SKIP_CHANGELOG = args['skip_changelog']
IGNORE_NEW = args['ignore_new']

if args['input_json'] is None and IGNORE_NEW == True:
	ERRORS.append("Can not ignore new input if no JSON file also specified.")

#If we are reading from a cached JSON file.
tmpSort = 0;
tmpDate = ""
if len(INPUT_JSON) != 0:
	if os.path.isfile(INPUT_JSON):
		with open(INPUT_JSON) as JSONfile:
			RESULTS = json.load(JSONfile)
		JSONfile.close()
		#Re-Scan the release count and the versions array.
		#Look for the date of the most recent record.
		for result in RESULTS:
			if 'sortkey' in result:
				if result['sortkey'] > tmpSort:
					tmpSort = result['sortkey']
					if 'date' in result:
						tmpDate = result['date']
			if 'version' in result:
				if result['version'] not in VERSIONS:
					VERSIONS.append(result['version'])
			if 'release' in result:
				RELEASECOUNT = RELEASECOUNT + 1

		#Set the first date fields to only get changes since the latest date in the local cache.
		FIRSTDATE = datetime.datetime.strptime(tmpDate, "%Y-%m-%d")
		FIRSTDATE_TEXT = tmpDate

	else:
		ERRORS.append("JSON input file '" + str(INPUT_JSON) + "' not found.")

#If we are reading repositories, etc.
#else:
if not IGNORE_NEW:
	#Get the GitHub commits from the local repository
	for commit in Repository(GITHUB_REPO, since=FIRSTDATE, only_in_branch='master').traverse_commits():

		print(commit.merge, commit.hash)
		#Change the committer_date to UTC because it is presented the local time of the commiter.
		tmpUTC = commit.committer_date + datetime.timedelta(seconds=commit.committer_timezone)
		tmpUTC = tmpUTC.replace(tzinfo=datetime.timezone.utc)

		tmpObj = {}
		tmpObj['date'] = tmpUTC.strftime('%Y-%m-%d')
		tmpObj['sortkey'] = int(tmpUTC.strftime('%Y%m%d0'))
		messageLines = commit.msg.strip().splitlines()
		#If the commit message is empty, create one.
		if len(messageLines) == 0:
			messageLines = []
			messageLines.append("Commit: " + commit.hash[0:8])

		#If the author is the translation bot, then sanitise the commit name.
		if commit.author.name in INTL_NAMES:
			if messageLines[0][0:16] == "intl: Translate " or messageLines[0][0:11] == "transifex: ":
				#Get the last word from the first line of the message, that is the language code.
				langWords = messageLines[0].split(" ")
				#Add a custom line to the beginning of the message lines.
				messageLines.insert(0, "Translation for '" + langWords[-1] + "' updated.")
		tmpObj['text'] = messageLines
		tmpObj['url'] = "https://github.com/tvheadend/tvheadend/commit/" + commit.hash
		tmpObj['hash'] = commit.hash
		RESULTS.append(tmpObj)
		

	#Get the GitHub commits via the API (old method, TODO: Remove)
	#loopFlag = True
	loopFlag = False #Bypass github API for now.
	pageNum = 1
	while loopFlag:
		pageData = getPage(pageNum, "GH")
		#print(len(pageData))

		for commit in pageData:
			tmpObj = {}
			tmpObj['date'] = commit['commit']['committer']['date'][0:10]  #This seems to always be expressed as UTC.
			tmpObj['sortkey'] = int(commit['commit']['committer']['date'][0:4] + commit['commit']['committer']['date'][5:7] + commit['commit']['committer']['date'][8:10] + "0")
			messageLines = commit['commit']['message'].strip().splitlines()
			#TODO - Do markdown control characters in the commit message need to be escaped?
			#https://docs.gitbook.com/content-editor/editing-content/markdown
			#Remove leading empty lines from the GitHub commit message
			while len(messageLines[0]) == 0:
				del messageLines[0]
			#Special handling for translation updates.
			#Check to see if the commit author is in the list of translation authors.
			if 'author' in commit['commit']:
				if 'name' in commit['commit']['author']:
					if commit['commit']['author']['name'] in INTL_NAMES:
						if messageLines[0][0:16] == "intl: Translate " or messageLines[0][0:11] == "transifex: ":
							#Get the last word from the first line of the message, that is the language code.
							langWords = messageLines[0].split(" ")
							#Add a custom line to the beginning of the message lines.
							messageLines.insert(0, "Translation for '" + langWords[-1] + "' updated.")
			tmpObj['text'] = messageLines
			tmpObj['url'] = commit['html_url']
			tmpObj['hash'] = commit['sha']
			RESULTS.append(tmpObj)

		pageNum += 1
		if len(pageData) < PERPAGE:
		#if pageNum > 3:
			loopFlag = False

	#Get the Cloudsmith releases via the API.
	pageNum = 1
	loopFlag = True
	while loopFlag:
		pageData = getPage(pageNum, "CS")
		#print(len(pageData))

		for rel in pageData:
			tmpObj = {}
			tmpVer = rel['version'].split("~")[0]
			#Only track unique version numbers (Each 'version' has several platform packages created.)
			if tmpVer not in VERSIONS:
				VERSIONS.append(tmpVer)
				tmpObj['date'] = rel['status_updated_at'][0:10]  #This seems to always be expressed as UTC.
				tmpObj['sortkey'] = int(rel['status_updated_at'][0:4] + rel['status_updated_at'][5:7] + rel['status_updated_at'][8:10] + "9")
				tmpObj['version'] = tmpVer
				if 'tags' in rel:
					#TODO - This is a proof-of-concept.
					#       Once releases start, the actual release tag
					#       will need to be tested for and saved.
					if 'release' in rel['tags']:
					#if 'version' in rel['tags']:
						#print(rel['tags']['version'][0])
						tmpObj['release'] = str(rel['tags']['release'][0])
						#tmpObj['release'] = str(rel['tags']['version'][0])
						RELEASECOUNT = RELEASECOUNT + 1
				##TODO - Remove this dummy code that forces some 'releases'
				#if tmpVer.find("6") > 1:
				#	RELEASECOUNT = RELEASECOUNT + 1
				#	tmpObj['release'] = "12.34." + str(RELEASECOUNT)
				##TODO - End remove dummy code
				RESULTS.append(tmpObj)

		pageNum += 1
		if len(pageData) < PERPAGE:
		#if pageNum > 3:
			loopFlag = False

#Sort all of the data by date, prioritising so that Cloudsmith comes before GitHub.
RESULTS.sort(reverse=True, key=lambda x: x['sortkey'])

#Write the output to the MD file
output = open(OUTPUT_FILE,"w")
output.write("---\n")
output.write("layout:\n")
output.write("  title:\n")
output.write("    visible: true\n")
output.write("  description:\n")
output.write("    visible: false\n")
output.write("  tableOfContents:\n")
output.write("    visible: true\n")
output.write("  outline:\n")
output.write("    visible: true\n")
output.write("  pagination:\n")
output.write("    visible: true\n")
output.write("---\n")
output.write("\n")
output.write("# Release / Change Log\n")  #<--- This is the page main header
output.write("\n")

#If there were any errors fetching the API data, report them at the top of the document.
if len(ERRORS) != 0:
	output.write("**WARNING: Errors Encountered**\n\n")
	for err in ERRORS:
		output.write(err + "\n\n")

#If any releases have been found, list the first one with commit messages but not nightly builds.
if not SKIP_LATEST:
	if RELEASECOUNT != 0:
		outputBody(output, True)

#If any releases have been found, list 2 to 7
relCount = 0
if not SKIP_RECENT:
	if RELEASECOUNT > 1:
		output.write("## Recent Releases\n")
		for rel in RESULTS:
			if 'release' in rel:
				if relCount != 0:
					output.write("### [Release " + rel['release'] + "](" + cloudsmithURL(rel) + ") (" + rel['date'] + ")\n")
				relCount = relCount + 1
				#Only show the releases 2 to 7
				if relCount > 6:
					break

#Output the main body of the document
if not SKIP_CHANGELOG:
	output.write("## Releases, Nightly Builds and Change Log\n")
	outputBody(output, False)


#Add date/time stamp at the end of the main text.
output.write("\n[**Automatically generated: " + datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')  + "**](#user-content-fn-" + str(ANNCOUNT) + ")[^" + str(ANNCOUNT) + "]\n\n")

#Build the run notes to add as an annotation to the datestamp.
for arg in args:
	RUN_NOTES.append("**" + arg + ":**  " + str(args[arg]))

RUN_NOTES.append("**First date fetched:** " + FIRSTDATE_TEXT)
RUN_NOTES.append("**Records found:** " + str(len(RESULTS)))

annObj = {}
annObj['index'] = ANNCOUNT
annObj['lines'] = RUN_NOTES
ANNOTATIONS.append(annObj)
ANNCOUNT = ANNCOUNT + 1

#Add the annotations to the end of the MD document.
for ann in ANNOTATIONS:
	output.write("\n[^" + str(ann['index']) +"]: " + ann['lines'][0] + "\n\n")
	for line in ann['lines'][1:]:
		if len(line) != 0:
			output.write("    " + line + "\n\n")

output.close()

#Output the JSON dump if required.
if len(OUTPUT_JSON) != 0:
	with open(OUTPUT_JSON, "w") as jsonfile:
		jsonfile.write(json.dumps(RESULTS, indent=4))
	jsonfile.close()

#If there were errors, ret the return code.
if len(ERRORS) == 0:
	sys.exit(0)
else:
	sys.exit(-1)

